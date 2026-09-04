"""
Business deduplication helpers.

Dedupe key is per-organization: normalized name + rounded lat/lng + normalized phone.
Matching is intentionally conservative — better a rare false-negative than merging two shops.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple


_PHONE_DIGITS = re.compile(r"\D+")
_NON_ALNUM = re.compile(r"[^a-z0-9\s]")
_MULTI_SPACE = re.compile(r"\s+")

# Common legal / noise suffixes stripped before compare
_NAME_SUFFIXES = re.compile(
    r"\b(ltd|llc|inc|gmbh|s\.?r\.?o\.?|sp\s*z\s*o\.?\s*o\.?|pty|co|company|"
    r"salon|studio|shop|store|the)\b",
    re.I,
)


def normalize_name(name: Optional[str]) -> str:
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = _NAME_SUFFIXES.sub(" ", text)
    text = _NON_ALNUM.sub(" ", text)
    text = _MULTI_SPACE.sub(" ", text).strip()
    return text


def normalize_phone(phone: Optional[str]) -> str:
    if not phone:
        return ""
    digits = _PHONE_DIGITS.sub("", phone)
    # Keep last 10–12 digits to compare across +country variants
    if len(digits) > 12:
        digits = digits[-12:]
    return digits


def normalize_website(url: Optional[str]) -> str:
    if not url:
        return ""
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("/")[0].split("?")[0]
    return u


def round_coord(value: Optional[float], places: int = 3) -> Optional[str]:
    """~100m precision at 3 decimal places — good for same-store matching."""
    if value is None:
        return None
    try:
        return f"{float(value):.{places}f}"
    except (TypeError, ValueError):
        return None


def compute_dedupe_key(
    name: Optional[str],
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    phone: Optional[str] = None,
    website_url: Optional[str] = None,
) -> str:
    """
    Stable fingerprint for unique constraint.
    Prefers name+geo; falls back to name+phone or name+website.
    """
    n = normalize_name(name)
    la = round_coord(latitude)
    lo = round_coord(longitude)
    ph = normalize_phone(phone)
    web = normalize_website(website_url)

    if n and la and lo:
        return f"n:{n}|g:{la},{lo}"
    if n and ph:
        return f"n:{n}|p:{ph}"
    if n and web:
        return f"n:{n}|w:{web}"
    if n:
        return f"n:{n}|solo"
    if ph:
        return f"p:{ph}"
    if web:
        return f"w:{web}"
    return f"unknown:{hash((name, latitude, longitude)) & 0xFFFFFFFF:x}"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, sin, cos, sqrt, atan2

    r = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def names_similar(a: str, b: str) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # Containment for "Joe's Barber" vs "Joes Barber Krakow"
    if na in nb or nb in na:
        return True
    # Token Jaccard
    ta, tb = set(na.split()), set(nb.split())
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    union = len(ta | tb)
    return (inter / union) >= 0.6


def merge_business_records(
    primary: Dict[str, Any],
    secondary: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge enrichment (e.g. Google Places) into an OSM seed.
    Never overwrite a non-empty primary field with empty secondary.
    Prefer higher review_count / rating from secondary when primary lacks them.
    """
    out = dict(primary)
    for key in (
        "phone",
        "website_url",
        "address",
        "category",
        "latitude",
        "longitude",
    ):
        if not out.get(key) and secondary.get(key):
            out[key] = secondary[key]

    # Reviews / rating almost always from Places
    if secondary.get("review_count") is not None:
        if out.get("review_count") is None or int(secondary["review_count"]) > int(out.get("review_count") or 0):
            out["review_count"] = int(secondary["review_count"])
    if secondary.get("rating") is not None:
        if out.get("rating") is None:
            out["rating"] = secondary["rating"]

    # Confidence: upgrade when enrichment fills gaps
    conf = dict(out.get("confidence") or {})
    sconf = secondary.get("confidence") or {}
    for k, v in sconf.items():
        if conf.get(k) in (None, "unknown", "not_found") and v:
            conf[k] = v
    if secondary.get("review_count") is not None:
        conf["reviews"] = "likely"
    out["confidence"] = conf

    # source_data audit trail
    src = dict(out.get("source_data") or {})
    src["enriched_from"] = secondary.get("source_data", {}).get("source") or secondary.get("source") or "enrichment"
    if secondary.get("source_data"):
        src["enrichment"] = secondary["source_data"]
    out["source_data"] = src
    return out


def dedupe_record_list(
    records: Iterable[Dict[str, Any]],
    proximity_m: float = 75.0,
) -> List[Dict[str, Any]]:
    """
    In-memory dedupe before DB insert.
    Groups by dedupe_key first, then proximity+name similarity.
    """
    items = list(records)
    if not items:
        return []

    # First pass: exact dedupe_key
    by_key: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for rec in items:
        if rec.get("error"):
            continue
        key = compute_dedupe_key(
            rec.get("name"),
            rec.get("latitude"),
            rec.get("longitude"),
            rec.get("phone"),
            rec.get("website_url"),
        )
        rec = {**rec, "dedupe_key": key}
        if key in by_key:
            by_key[key] = merge_business_records(by_key[key], rec)
        else:
            by_key[key] = rec
            order.append(key)

    merged = [by_key[k] for k in order]

    # Second pass: proximity cluster for near-duplicate keys
    kept: List[Dict[str, Any]] = []
    for rec in merged:
        matched_idx = None
        lat, lon = rec.get("latitude"), rec.get("longitude")
        for i, other in enumerate(kept):
            if not names_similar(str(rec.get("name") or ""), str(other.get("name") or "")):
                continue
            olat, olon = other.get("latitude"), other.get("longitude")
            if lat is not None and lon is not None and olat is not None and olon is not None:
                if haversine_m(float(lat), float(lon), float(olat), float(olon)) <= proximity_m:
                    matched_idx = i
                    break
            # Same normalized phone
            if normalize_phone(rec.get("phone")) and normalize_phone(rec.get("phone")) == normalize_phone(
                other.get("phone")
            ):
                matched_idx = i
                break
        if matched_idx is not None:
            kept[matched_idx] = merge_business_records(kept[matched_idx], rec)
        else:
            kept.append(rec)
    return kept
