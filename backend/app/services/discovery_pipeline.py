"""
Sync discovery pipeline for Celery workers.

OSM seed → optional Google Places enrichment → strong dedupe →
website intelligence audit (bounded) → score → Lead create.

Never called from a FastAPI request path — only from workers.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.website_audit import WebsiteAudit
from app.services.dedupe import compute_dedupe_key, dedupe_record_list
from app.services.discovery_service import DiscoveryService
from app.services.places_provider import (
    GooglePlacesProvider,
    match_places_to_osm,
)
from app.services.scoring_service import ScoringService
from app.services.website_intelligence import analyze_website_sync
from app.services.usage_service import get_remaining_lead_capacity_sync

logger = logging.getLogger(__name__)

MAX_WEBSITE_AUDITS_PER_RUN = 25
WEBSITE_RECrawl_DAYS = 30


def _analyze_website_sync(url: str) -> Dict[str, Any]:
    """Backward-compatible wrapper around the richer deterministic analyzer."""
    return analyze_website_sync(url)


def _collect_candidates(
    *,
    city: str,
    business_type: str,
    country: Optional[str],
    limit: int,
    places_api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """OSM seed + optional Places enrichment, then in-memory dedupe."""
    from app.demo.adapters import is_demo_mode

    if is_demo_mode():
        return _demo_candidates(city=city, business_type=business_type, limit=limit)

    discovery = DiscoveryService()
    osm = discovery.search_osm_sync(
        city=city,
        business_type=business_type,
        country=country,
        limit=limit,
    )
    if osm and isinstance(osm[0], dict) and "error" in osm[0]:
        osm_err = osm[0]["error"]
        logger.warning("OSM discovery error: %s — trying Places-only if enabled", osm_err)
        osm = []

    places_provider = GooglePlacesProvider.from_settings(override_key=places_api_key)
    places_rows: List[Dict[str, Any]] = []
    if places_provider:
        try:
            places_rows = places_provider.search_and_enrich(
                business_type=business_type,
                city=city,
                country=country,
                limit=min(limit, 40),
                fetch_details_max=12,
            )
            logger.info("Places returned %s rows for %s / %s", len(places_rows), business_type, city)
        except Exception:
            logger.exception("Places enrichment failed — continuing with OSM only")

    if osm and places_rows:
        combined = match_places_to_osm(osm, places_rows)
    elif places_rows:
        combined = places_rows
    else:
        combined = osm

    if not combined:
        return []

    deduped = dedupe_record_list(combined, proximity_m=75.0)
    logger.info(
        "Candidates after merge/dedupe: osm=%s places=%s final=%s",
        len(osm),
        len(places_rows),
        len(deduped),
    )
    return deduped


def _demo_candidates(
    *,
    city: Optional[str],
    business_type: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    """DEMO_MODE candidate source — local fixtures only, no network calls."""
    from app.demo.fixtures import filter_demo_businesses

    demo_rows = filter_demo_businesses(industry=business_type, city=city, limit=limit)
    candidates: List[Dict[str, Any]] = []
    for row in demo_rows:
        candidates.append(
            {
                "name": row["name"],
                "category": row.get("category"),
                "address": row.get("address"),
                "latitude": None,
                "longitude": None,
                "phone": row.get("phone"),
                "website_url": row.get("website_url"),
                "rating": row.get("rating"),
                "review_count": row.get("review_count"),
                "source": row.get("source") or "demo",
                "source_data": {"source": row.get("source") or "demo", "demo_mode": True},
                "confidence": {
                    "name": "likely",
                    "address": "likely",
                    "reviews": "likely",
                    "phone": "likely",
                    "website": "likely" if row.get("website_url") else "unknown",
                },
                "_demo_website_weak": bool(row.get("website_weak")),
                "_demo_has_booking": bool(row.get("has_booking")),
            }
        )
    return candidates


def _upsert_business(
    session: Session,
    *,
    organization_id: UUID,
    raw: Dict[str, Any],
) -> Business:
    """Insert business or return existing row for same org+dedupe_key."""
    key = raw.get("dedupe_key") or compute_dedupe_key(
        raw.get("name"),
        raw.get("latitude"),
        raw.get("longitude"),
        raw.get("phone"),
        raw.get("website_url"),
    )
    source = raw.get("source") or (raw.get("source_data") or {}).get("source") or "osm"

    existing = session.execute(
        select(Business).where(
            Business.organization_id == organization_id,
            Business.dedupe_key == key,
        )
    ).scalar_one_or_none()

    if existing:
        changed = False
        for field in ("phone", "website_url", "address", "category"):
            if not getattr(existing, field) and raw.get(field):
                setattr(existing, field, raw[field])
                changed = True
        if raw.get("review_count") is not None:
            if existing.review_count is None or int(raw["review_count"]) > int(existing.review_count or 0):
                existing.review_count = int(raw["review_count"])
                changed = True
        if raw.get("rating") is not None and existing.rating is None:
            existing.rating = float(raw["rating"])
            changed = True
        if changed:
            session.flush()
        return existing

    business = Business(
        organization_id=organization_id,
        name=raw["name"],
        category=raw.get("category"),
        address=raw.get("address"),
        latitude=raw.get("latitude"),
        longitude=raw.get("longitude"),
        phone=raw.get("phone"),
        website_url=raw.get("website_url"),
        rating=raw.get("rating"),
        review_count=raw.get("review_count"),
        source=str(source)[:40] if source else None,
        dedupe_key=key,
        source_data=raw.get("source_data"),
    )
    session.add(business)
    session.flush()
    return business


def run_discovery_pipeline_sync(session: Session, campaign_id: UUID) -> Dict[str, Any]:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        return {"error": "campaign_not_found", "campaign_id": str(campaign_id)}
    if campaign.status == "cancelled":
        return {"error": "campaign_cancelled", "campaign_id": str(campaign_id)}

    campaign.status = "discovering"
    session.commit()

    params = campaign.structured_params or {}
    city = params.get("city")
    business_type = params.get("business_type") or params.get("category")
    country = params.get("country")
    limit = int(params.get("limit") or 50)
    places_key = params.get("google_places_api_key")

    if not city or not business_type:
        field_values = {"city": city, "business_type": business_type}
        missing_fields = [f for f in ("city", "business_type") if not field_values[f]]
        message = f"Missing required parameter(s): {', '.join(missing_fields)}"
        logger.warning("discovery.validation_failed campaign=%s missing=%s", campaign_id, missing_fields)
        campaign.status = "failed"
        session.commit()
        return {
            "error": "validation_error",
            "message": message,
            "missing_fields": missing_fields,
            "campaign_id": str(campaign_id),
        }

    try:
        candidates = _collect_candidates(
            city=city,
            business_type=business_type,
            country=country,
            limit=limit,
            places_api_key=places_key,
        )
    except Exception as exc:
        logger.exception("candidate collection failed")
        campaign.status = "failed"
        session.commit()
        return {"error": str(exc), "campaign_id": str(campaign_id)}

    if not candidates:
        campaign.total_leads_found = 0
        campaign.qualified_leads = 0
        campaign.status = "ready_for_review"
        session.commit()
        return {
            "campaign_id": str(campaign_id),
            "total_found": 0,
            "qualified": 0,
            "note": "No businesses found (OSM sparse and Places disabled/empty)",
            "status": campaign.status,
        }

    existing_lead_biz = {
        row[0]
        for row in session.execute(
            select(Lead.business_id).where(Lead.campaign_id == campaign_id)
        ).all()
    }

    filters = params.get("filters") or {}
    scorer = ScoringService()
    created_leads = 0
    audited = 0
    total_found = len(candidates)
    quota_reached = False
    remaining_lead_capacity = get_remaining_lead_capacity_sync(
        session,
        campaign.organization_id,
    )
    campaign.status = "scoring"
    session.commit()

    if remaining_lead_capacity <= 0:
        quota_reached = True
        logger.info(
            "Discovery skipped: monthly lead quota already reached campaign=%s",
            campaign_id,
        )

    for raw in candidates:
        if quota_reached:
            break

        if campaign.status == "cancelled":
            session.refresh(campaign)
            if campaign.status == "cancelled":
                break

        business = _upsert_business(
            session,
            organization_id=campaign.organization_id,
            raw=raw,
        )

        if business.id in existing_lead_biz:
            continue

        if raw.get("phone"):
            exists_phone = session.execute(
                select(Contact.id).where(
                    Contact.business_id == business.id,
                    Contact.type == "phone",
                    Contact.value == raw["phone"],
                )
            ).scalar_one_or_none()
            if not exists_phone:
                session.add(
                    Contact(
                        business_id=business.id,
                        type="phone",
                        value=raw["phone"],
                        confidence_state=(raw.get("confidence") or {}).get("phone", "unknown"),
                        consent_state="PUBLICLY_LISTED_BUSINESS_CONTACT",
                    )
                )

        has_website = bool(business.website_url or raw.get("website_url"))
        website_url = business.website_url or raw.get("website_url")
        website_weak = False
        has_booking = False
        website_intelligence: Dict[str, Any] = {}

        if has_website and website_url and raw.get("_demo_website_weak") is not None:
            website_weak = bool(raw.get("_demo_website_weak"))
            has_booking = bool(raw.get("_demo_has_booking"))
            website_intelligence = {
                "schema_version": 2,
                "demo_mode": True,
                "quality_score": 40 if website_weak else 85,
                "weak_reasons": ["fixture_weak_website"] if website_weak else [],
                "booking_vendor": "demo_booking" if has_booking else None,
            }
            session.add(
                WebsiteAudit(
                    business_id=business.id,
                    url=website_url,
                    http_status=200,
                    has_ssl=website_url.startswith("https://"),
                    has_viewport=not website_weak,
                    booking_vendor_detected="demo_booking" if has_booking else None,
                    raw_findings=website_intelligence,
                    crawled_at=datetime.now(timezone.utc),
                    next_recrawl_at=datetime.now(timezone.utc) + timedelta(days=WEBSITE_RECrawl_DAYS),
                )
            )
        elif has_website and website_url:
            now = datetime.now(timezone.utc)
            prior = session.execute(
                select(WebsiteAudit)
                .where(WebsiteAudit.business_id == business.id)
                .order_by(WebsiteAudit.crawled_at.desc().nullslast())
                .limit(1)
            ).scalar_one_or_none()

            recent = bool(prior and prior.next_recrawl_at and prior.next_recrawl_at > now)
            if prior and recent:
                has_booking = bool(prior.booking_vendor_detected)
                website_intelligence = prior.raw_findings if isinstance(prior.raw_findings, dict) else {}
                website_weak = bool(
                    website_intelligence.get("weak_reasons")
                    or prior.has_ssl is False
                    or prior.has_viewport is False
                    or (website_intelligence.get("quality_score") is not None and int(website_intelligence["quality_score"]) < 60)
                )
            elif audited < MAX_WEBSITE_AUDITS_PER_RUN:
                audit_data = _analyze_website_sync(website_url)
                audited += 1
                has_booking = bool(audit_data.get("booking_vendor_detected"))
                website_intelligence = audit_data.get("raw_findings") or {}
                quality_score = website_intelligence.get("quality_score")
                weak_reasons = website_intelligence.get("weak_reasons") or []
                website_weak = bool(
                    (quality_score is not None and int(quality_score) < 60)
                    or audit_data.get("has_ssl") is False and audit_data.get("has_viewport") is False
                )
                crawl_time = now
                session.add(
                    WebsiteAudit(
                        business_id=business.id,
                        url=website_url,
                        http_status=audit_data.get("http_status"),
                        has_ssl=audit_data.get("has_ssl"),
                        has_viewport=audit_data.get("has_viewport"),
                        booking_vendor_detected=audit_data.get("booking_vendor_detected"),
                        raw_findings=website_intelligence,
                        crawled_at=crawl_time,
                        next_recrawl_at=crawl_time + timedelta(days=WEBSITE_RECrawl_DAYS),
                    )
                )
            else:
                logger.info("website audit budget exhausted campaign=%s", campaign_id)

        if filters.get("no_website") and has_website and not website_weak:
            continue
        if filters.get("no_booking") and has_booking:
            continue

        review_count = business.review_count
        if review_count is None:
            review_count = raw.get("review_count")

        score_result = scorer.calculate_score(
            has_website=has_website,
            website_weak=website_weak,
            review_count=review_count,
            has_booking=has_booking,
            confidence=raw.get("confidence") or {},
        )

        lead = Lead(
            campaign_id=campaign.id,
            business_id=business.id,
            opportunity_score=score_result["opportunity_score"],
            score_breakdown={
                "rules": score_result["breakdown"],
                "website_intelligence": website_intelligence,
                "website_weak": website_weak,
                "has_booking": has_booking,
                "review_count_used": review_count,
                "data_sources": list(
                    {
                        raw.get("source") or (raw.get("source_data") or {}).get("source") or "osm",
                        *(["google_places"] if (raw.get("source_data") or {}).get("enriched_from") == "google_places" or raw.get("source") == "google_places" else []),
                    }
                ),
            },
            stage="new",
            confidence_summary=raw.get("confidence"),
        )
        session.add(lead)
        created_leads += 1
        remaining_lead_capacity -= 1
        existing_lead_biz.add(business.id)
        if remaining_lead_capacity <= 0:
            quota_reached = True
            logger.info(
                "Discovery reached monthly lead quota campaign=%s created=%s",
                campaign_id,
                created_leads,
            )

    campaign.total_leads_found = total_found
    campaign.qualified_leads = created_leads
    campaign.status = "ready_for_review"
    if created_leads > 0:
        from app.services.usage_service import increment_usage_sync
        increment_usage_sync(
            session,
            campaign.organization_id,
            "leads_count",
            amount=created_leads,
        )
    session.commit()

    note = None
    if quota_reached:
        note = "Monthly lead quota reached; discovery stopped at the plan limit."

    logger.info(
        "Discovery done campaign=%s found=%s qualified=%s audited=%s quota_reached=%s",
        campaign_id,
        total_found,
        created_leads,
        audited,
        quota_reached,
    )
    return {
        "campaign_id": str(campaign_id),
        "total_found": total_found,
        "qualified": created_leads,
        "website_audits": audited,
        "status": campaign.status,
        **({"note": note} if note else {}),
    }
