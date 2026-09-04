"""Deterministic website intelligence for lead qualification.

The analyzer is intentionally rule-based: it never calls an LLM and never
changes the opportunity score itself. Network access must go through
``safe_fetch`` so SSRF protections remain in force.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.security.safe_fetch import SafeFetchError, safe_fetch

BOOKING_VENDORS = (
    "calendly", "square.site", "squareup", "setmore", "booksy", "fresha",
    "mindbody", "acuityscheduling", "simplybook", "schedulicity", "vagaro",
    "boulevard", "zenoti", "reservio", "appointy", "youcanbook.me",
)
CMS_SIGNATURES = {
    "wordpress": ("wp-content", "wp-includes", "wordpress"),
    "wix": ("wixstatic.com", "wix.com"),
    "squarespace": ("squarespace", "static1.squarespace.com"),
    "shopify": ("cdn.shopify.com", "shopify"),
    "webflow": ("webflow", "assets.website-files.com"),
    "godaddy": ("godaddy", "secureserver.net"),
    "weebly": ("weebly", "editmysite.com"),
}
ANALYTICS_SIGNATURES = {
    "google_analytics": ("google-analytics.com", "gtag(", "googletagmanager.com"),
    "meta_pixel": ("connect.facebook.net", "fbq("),
    "hotjar": ("hotjar.com", "hj("),
}
SOCIAL_HOSTS = (
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com", "tiktok.com",
)


def _clean(value: Optional[str], limit: int = 300) -> Optional[str]:
    if not value:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit] or None


def _find_signature(lower: str, signatures: Dict[str, tuple[str, ...]]) -> list[str]:
    return [name for name, needles in signatures.items() if any(n in lower for n in needles)]


def analyze_website_sync(url: str) -> Dict[str, Any]:
    """Fetch and deterministically profile one public website.

    Returns a stable JSON-friendly structure suitable for WebsiteAudit.raw_findings.
    Fetch failures are represented as findings instead of raising, so one bad
    website cannot abort a discovery run.
    """
    settings = get_settings()
    max_bytes = int(getattr(settings, "WEBSITE_FETCH_MAX_BYTES", 5_242_880))
    timeout = float(getattr(settings, "WEBSITE_FETCH_TIMEOUT_SECONDS", 10))
    result: Dict[str, Any] = {
        "schema_version": 2,
        "http_status": None,
        "final_url": None,
        "has_ssl": None,
        "has_viewport": None,
        "booking_vendor_detected": None,
        "raw_findings": {},
    }
    try:
        response = safe_fetch(url, timeout=timeout, max_bytes=max_bytes)
        final_url = str(getattr(response, "url", url))
        text = str(getattr(response, "text", ""))[:max_bytes]
        soup = BeautifulSoup(text, "html.parser")
        lower = text.lower()
        parsed = urlparse(final_url)

        title = _clean(soup.title.get_text(" ", strip=True) if soup.title else None, 180)
        description_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        description = _clean(description_tag.get("content") if description_tag else None, 300)
        canonical_tag = soup.find("link", attrs={"rel": lambda v: v and "canonical" in v})
        canonical = _clean(canonical_tag.get("href") if canonical_tag else None, 500)
        h1s = [_clean(x.get_text(" ", strip=True), 180) for x in soup.find_all("h1")]
        h1s = [x for x in h1s if x]

        viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)}) is not None
        forms = soup.find_all("form")
        links = [a.get("href") for a in soup.find_all("a", href=True)]
        text_content = soup.get_text(" ", strip=True)
        emails = sorted(set(re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)))[:10]
        tel_links = sorted(set(a[7:] for a in links if isinstance(a, str) and a.lower().startswith("tel:")))[:10]
        social_links = sorted({
            href for href in links
            if isinstance(href, str) and any(host in href.lower() for host in SOCIAL_HOSTS)
        })[:10]

        booking = next((v for v in BOOKING_VENDORS if v in lower), None)
        cms = _find_signature(lower, CMS_SIGNATURES)
        analytics = _find_signature(lower, ANALYTICS_SIGNATURES)
        has_https = parsed.scheme.lower() == "https"
        has_favicon = soup.find("link", attrs={"rel": lambda v: v and "icon" in v}) is not None
        has_robots_link = any(isinstance(h, str) and "/robots.txt" in h.lower() for h in links)
        has_cta = any(re.search(r"\b(book|schedule|appointment|contact|call|quote|consult|reserve|shop|buy)\b", a, re.I) for a in [x.get_text(" ", strip=True) for x in soup.find_all("a")])
        image_count = len(soup.find_all("img"))
        images_missing_alt = sum(1 for img in soup.find_all("img") if not _clean(img.get("alt"), 1))
        scripts = len(soup.find_all("script"))
        external_scripts = sum(1 for s in soup.find_all("script", src=True) if urlparse(urljoin(final_url, s.get("src"))).netloc not in ("", parsed.netloc))

        broken_meta = {
            "missing_title": not bool(title),
            "missing_description": not bool(description),
            "missing_h1": not bool(h1s),
            "missing_viewport": not viewport,
            "missing_favicon": not has_favicon,
        }
        accessibility = {
            "images": image_count,
            "images_missing_alt": images_missing_alt,
            "alt_coverage": round((image_count - images_missing_alt) / image_count, 3) if image_count else 1.0,
        }
        quality_penalties = sum([
            25 if not has_https else 0,
            20 if not viewport else 0,
            15 if not title else 0,
            10 if not description else 0,
            10 if not h1s else 0,
            10 if not has_cta else 0,
            10 if image_count and images_missing_alt / image_count > 0.5 else 0,
        ])
        quality_score = max(0, 100 - quality_penalties)

        result.update({
            "http_status": getattr(response, "status_code", None),
            "final_url": final_url,
            "has_ssl": has_https,
            "has_viewport": viewport,
            "booking_vendor_detected": booking,
            "raw_findings": {
                "schema_version": 2,
                "title": title,
                "meta_description": description,
                "canonical_url": canonical,
                "h1_count": len(h1s),
                "h1s": h1s[:10],
                "word_count": len(text_content.split()),
                "html_bytes": len(text.encode("utf-8", errors="ignore")),
                "forms": len(forms),
                "has_contact_form": any(any(k in str(f).lower() for k in ("contact", "message", "email")) for f in forms),
                "has_cta": has_cta,
                "emails": emails,
                "phone_links": tel_links,
                "social_links": social_links,
                "social_presence_count": len(social_links),
                "booking_vendor": booking,
                "cms": cms,
                "analytics": analytics,
                "favicon": has_favicon,
                "robots_link_detected": has_robots_link,
                "images": image_count,
                "accessibility": accessibility,
                "scripts": scripts,
                "external_scripts": external_scripts,
                "mobile_readiness": {
                    "viewport": viewport,
                    "responsive_css_signals": any(x in lower for x in ("@media", "responsive", "bootstrap", "tailwind")),
                },
                "seo": broken_meta,
                "quality_score": quality_score,
                "weak_reasons": [k for k, v in broken_meta.items() if v] + (["no_https"] if not has_https else []) + (["no_cta"] if not has_cta else []),
            },
        })
    except SafeFetchError as exc:
        result["raw_findings"] = {"schema_version": 2, "error": f"{exc.code}: {exc.message}", "ssrf_blocked": True}
    except Exception as exc:
        result["raw_findings"] = {"schema_version": 2, "error": str(exc)[:300]}
    return result
