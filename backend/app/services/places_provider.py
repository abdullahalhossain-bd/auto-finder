"""
Optional Google Places enrichment.

- Requires org/platform API key (never a shared bill-shock key by default).
- Used only when GOOGLE_PLACES_ENABLED=true AND a non-placeholder key is provided.
- Fills review_count, rating, phone, website gaps that OSM often lacks.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.services.dedupe import haversine_m, names_similar

logger = logging.getLogger(__name__)

TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


class GooglePlacesProvider:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key.strip()
        self.http_timeout = 25.0

    @classmethod
    def from_settings(cls, override_key: Optional[str] = None) -> Optional["GooglePlacesProvider"]:
        settings = get_settings()
        if not getattr(settings, "GOOGLE_PLACES_ENABLED", False):
            return None
        key = (override_key or getattr(settings, "GOOGLE_PLACES_API_KEY", "") or "").strip()
        if not key or key in ("changeme", "your-key-here"):
            # GOOGLE_PLACES_ENABLED=true with no real key is a config mistake,
            # not a silent no-op — surface it clearly (Places is optional
            # enrichment, so discovery still proceeds OSM-only; requirement
            # is just that the missing key isn't swallowed silently).
            logger.warning(
                "Google Places is enabled (GOOGLE_PLACES_ENABLED=true) but no valid "
                "GOOGLE_PLACES_API_KEY is configured — continuing with OSM-only "
                "discovery (no Places enrichment)."
            )
            return None
        return cls(api_key=key)

    def text_search(
        self,
        *,
        query: str,
        limit: int = 40,
    ) -> List[Dict[str, Any]]:
        """
        Places Text Search → normalized business dicts with review_count/rating.
        """
        results: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        with httpx.Client(timeout=self.http_timeout) as client:
            while len(results) < limit:
                params: Dict[str, str] = {
                    "query": query,
                    "key": self.api_key,
                }
                if page_token:
                    params["pagetoken"] = page_token
                try:
                    resp = client.get(TEXT_SEARCH_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    logger.warning("Places text_search failed: %s", exc)
                    break

                status = data.get("status")
                if status not in ("OK", "ZERO_RESULTS"):
                    logger.warning("Places status=%s error=%s", status, data.get("error_message"))
                    break

                for item in data.get("results") or []:
                    results.append(self._normalize_text_result(item))
                    if len(results) >= limit:
                        break

                page_token = data.get("next_page_token")
                if not page_token:
                    break
                # Google requires a short delay before next_page_token is valid
                import time

                time.sleep(2.0)

        return results[:limit]

    def _normalize_text_result(self, item: dict) -> Dict[str, Any]:
        loc = (item.get("geometry") or {}).get("location") or {}
        return {
            "name": item.get("name") or "Unknown",
            "category": (item.get("types") or [None])[0],
            "address": item.get("formatted_address"),
            "latitude": loc.get("lat"),
            "longitude": loc.get("lng"),
            "phone": None,  # needs Details call
            "website_url": None,
            "rating": item.get("rating"),
            "review_count": item.get("user_ratings_total"),
            "place_id": item.get("place_id"),
            "source": "google_places",
            "source_data": {
                "source": "google_places",
                "place_id": item.get("place_id"),
                "types": item.get("types"),
                "business_status": item.get("business_status"),
            },
            "confidence": {
                "name": "likely",
                "address": "likely" if item.get("formatted_address") else "unknown",
                "reviews": "likely" if item.get("user_ratings_total") is not None else "unknown",
                "phone": "unknown",
                "website": "unknown",
            },
        }

    def enrich_details(self, place_id: str) -> Dict[str, Any]:
        """Fetch phone + website for a place_id."""
        params = {
            "place_id": place_id,
            "fields": "formatted_phone_number,international_phone_number,website,url,user_ratings_total,rating",
            "key": self.api_key,
        }
        try:
            with httpx.Client(timeout=self.http_timeout) as client:
                resp = client.get(DETAILS_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
            if data.get("status") != "OK":
                return {}
            r = data.get("result") or {}
            phone = r.get("international_phone_number") or r.get("formatted_phone_number")
            return {
                "phone": phone,
                "website_url": r.get("website"),
                "rating": r.get("rating"),
                "review_count": r.get("user_ratings_total"),
            }
        except Exception as exc:
            logger.warning("Places details failed place_id=%s: %s", place_id, exc)
            return {}

    def search_and_enrich(
        self,
        *,
        business_type: str,
        city: str,
        country: Optional[str] = None,
        limit: int = 40,
        fetch_details_max: int = 15,
    ) -> List[Dict[str, Any]]:
        where = f"{city}" + (f", {country}" if country else "")
        query = f"{business_type} in {where}"
        rows = self.text_search(query=query, limit=limit)
        # Details for top N missing phone/website
        detailed = 0
        for row in rows:
            if detailed >= fetch_details_max:
                break
            pid = row.get("place_id")
            if not pid:
                continue
            if row.get("phone") and row.get("website_url"):
                continue
            extra = self.enrich_details(str(pid))
            if extra.get("phone"):
                row["phone"] = extra["phone"]
                row.setdefault("confidence", {})["phone"] = "likely"
            if extra.get("website_url"):
                row["website_url"] = extra["website_url"]
                row.setdefault("confidence", {})["website"] = "likely"
            if extra.get("review_count") is not None:
                row["review_count"] = extra["review_count"]
            if extra.get("rating") is not None:
                row["rating"] = extra["rating"]
            detailed += 1
        return rows


def match_places_to_osm(
    osm_records: List[Dict[str, Any]],
    places_records: List[Dict[str, Any]],
    proximity_m: float = 120.0,
) -> List[Dict[str, Any]]:
    """
    Attach Places review/rating/phone/website onto OSM seeds when name+distance match.
    Unmatched Places rows are appended as additional candidates (source=google_places).
    """
    from app.services.dedupe import merge_business_records

    used_places = set()
    enriched: List[Dict[str, Any]] = []

    for osm in osm_records:
        best_j = None
        best_dist = proximity_m + 1
        olat, olon = osm.get("latitude"), osm.get("longitude")
        for j, pl in enumerate(places_records):
            if j in used_places:
                continue
            if not names_similar(str(osm.get("name") or ""), str(pl.get("name") or "")):
                continue
            plat, plon = pl.get("latitude"), pl.get("longitude")
            if olat is None or olon is None or plat is None or plon is None:
                continue
            d = haversine_m(float(olat), float(olon), float(plat), float(plon))
            if d < best_dist:
                best_dist = d
                best_j = j
        if best_j is not None:
            used_places.add(best_j)
            enriched.append(merge_business_records(osm, places_records[best_j]))
        else:
            enriched.append(osm)

    # Add unmatched Places businesses (fills sparse OSM regions)
    for j, pl in enumerate(places_records):
        if j not in used_places:
            enriched.append(pl)

    return enriched