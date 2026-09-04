"""
Website Analysis Service
- Deterministic checks only
- All outbound fetches go through safe_fetch (SSRF guard)
"""
from typing import Dict, Any, Optional

from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.security.safe_fetch import SafeFetchError, safe_fetch_async


class WebsiteAnalysisService:
    """Perform deterministic website checks."""

    KNOWN_BOOKING_VENDORS = [
        "calendly.com",
        "fresha.com",
        "booksy.com",
        "vagaro.com",
        "square.site",
        "setmore.com",
        "simplybook.me",
    ]

    async def analyze(self, url: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "url": url,
            "http_status": None,
            "has_ssl": url.startswith("https://") if url else False,
            "has_viewport": False,
            "booking_vendor_detected": None,
            "raw_findings": {},
        }
        if not url:
            return result

        settings = get_settings()
        try:
            resp = await safe_fetch_async(
                url,
                timeout=float(getattr(settings, "WEBSITE_FETCH_TIMEOUT_SECONDS", 10)),
                max_bytes=int(getattr(settings, "WEBSITE_FETCH_MAX_BYTES", 5_242_880)),
            )
            result["http_status"] = resp.status_code
            result["has_ssl"] = str(resp.url).startswith("https://")
            text = resp.text
            soup = BeautifulSoup(text, "html.parser")
            viewport = soup.find("meta", attrs={"name": "viewport"})
            result["has_viewport"] = viewport is not None
            page_text = text.lower()
            for vendor in self.KNOWN_BOOKING_VENDORS:
                if vendor in page_text:
                    result["booking_vendor_detected"] = vendor
                    break
            result["raw_findings"] = {
                "title": soup.title.string if soup.title else None,
            }
        except SafeFetchError as e:
            result["raw_findings"]["error"] = f"{e.code}: {e.message}"
            result["raw_findings"]["ssrf_blocked"] = True
        except Exception as e:
            result["raw_findings"]["error"] = str(e)[:300]

        return result
