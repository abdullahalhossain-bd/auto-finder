"""
Public growth endpoints — no auth.
Rate-limited by global middleware. Used for top-of-funnel tools.
"""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.services.scoring_service import ScoringService
from app.services.website_analysis_service import WebsiteAnalysisService
from app.core.logging_config import log_event

router = APIRouter(prefix="/public", tags=["public"])

_URL_RE = re.compile(r"^https?://", re.I)


class WebsiteCheckRequest(BaseModel):
    url: str = Field(..., min_length=4, max_length=500)
    business_name: Optional[str] = Field(None, max_length=200)

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("url required")
        if not _URL_RE.match(v):
            v = "https://" + v
        return v[:500]


class WaitlistRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    role: Optional[str] = Field(None, max_length=80)  # agency | freelancer | founder
    city: Optional[str] = Field(None, max_length=80)


@router.post("/check-website")
async def check_website(body: WebsiteCheckRequest, request: Request):
    """
    Free opportunity check — growth magnet.
    Returns rule-based fitness style signals (not LLM).
    """
    analyzer = WebsiteAnalysisService()
    audit = await analyzer.analyze(body.url)

    has_website = True
    err = (audit.get("raw_findings") or {}).get("error")
    if err or audit.get("http_status") in (None, 0):
        # unreachable ≈ weak/no usable site for prospects
        has_website = False
    http = audit.get("http_status")
    if isinstance(http, int) and http >= 400:
        has_website = False

    website_weak = False
    if has_website:
        if not audit.get("has_ssl") or not audit.get("has_viewport"):
            website_weak = True
        if audit.get("http_status") and int(audit["http_status"]) >= 400:
            website_weak = True

    has_booking = bool(audit.get("booking_vendor_detected"))

    score = ScoringService().calculate_score(
        has_website=has_website,
        website_weak=website_weak,
        review_count=None,
        has_booking=has_booking,
        confidence={},
    )

    # Invert narrative for public tool: high score = opportunity for agency
    opportunity = float(score["opportunity_score"])
    if not has_website:
        headline = "Strong outreach opportunity — site missing or unreachable"
    elif not has_booking and website_weak:
        headline = "Good fit — weak site and no clear online booking"
    elif not has_booking:
        headline = "Possible fit — traffic signals without booking vendor"
    else:
        headline = "Lower priority — site + booking signals present"

    log_event(
        "growth.website_check",
        path=str(request.url.path),
        has_booking=has_booking,
        score=opportunity,
    )

    return {
        "url": body.url,
        "business_name": body.business_name,
        "headline": headline,
        "opportunity_score": opportunity,
        "tier": score.get("tier"),
        "tier_label": score.get("tier_label"),
        "signals": {
            "reachable": has_website,
            "ssl": audit.get("has_ssl"),
            "mobile_viewport": audit.get("has_viewport"),
            "booking_vendor": audit.get("booking_vendor_detected"),
            "http_status": audit.get("http_status"),
        },
        "breakdown": score.get("breakdown"),
        "method": "rule_based_opportunity_fit_v1",
        "cta": {
            "message": "Find more businesses like this in your city — free plan includes lead quota.",
            "register_path": "/register",
        },
    }


@router.post("/waitlist")
async def waitlist(body: WaitlistRequest, request: Request):
    """Capture interest when user is not ready to register — log for CRM export."""
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, detail={"error": {"code": "INVALID_EMAIL", "message": "Invalid email"}})

    log_event(
        "growth.waitlist",
        email=email,
        role=body.role,
        city=body.city,
        ip=(request.client.host if request.client else None),
    )
    # Console path — production wires ESP/CRM
    return {
        "ok": True,
        "message": "You're on the list. We'll reach out with city playbooks and early tips.",
    }


@router.get("/stats")
async def public_stats():
    """Soft social proof numbers — static/config friendly defaults for marketing."""
    from app.core.config import get_settings
    s = get_settings()
    return {
        "free_lead_quota": 40,
        "trial_days": int(getattr(s, "TRIAL_LENGTH_DAYS", 14) or 14),
        "tagline": "Find local businesses that need a website or booking — then outreach safely.",
        "differentiators": [
            "Opportunity score from site/booking gaps",
            "Human approval before every send",
            "SPF/DKIM required — not a spam cannon",
        ],
    }
