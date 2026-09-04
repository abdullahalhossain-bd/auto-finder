"""
Live DNS checks for SPF / DKIM / DMARC (free — dnspython or empty fallback).

Stage 1: best-effort. Failures return verified=False with reason, never raise to caller.
"""
from __future__ import annotations

from typing import Any, Optional

def _lookup_txt(name: str) -> list[str]:
    """Return TXT strings for name. Prefer dnspython; fallback empty."""
    try:
        import dns.resolver  # type: ignore

        answers = dns.resolver.resolve(name, "TXT")
        out: list[str] = []
        for rdata in answers:
            parts = getattr(rdata, "strings", None)
            if parts:
                out.append(
                    "".join(
                        p.decode("utf-8", "ignore") if isinstance(p, bytes) else str(p)
                        for p in parts
                    )
                )
            else:
                out.append(str(rdata).strip('"'))
        return out
    except Exception:
        return []


def check_spf(domain: str, *, require_include: Optional[str] = None) -> dict[str, Any]:
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain:
        return {"verified": False, "reason": "empty_domain", "records": []}
    records = _lookup_txt(domain)
    spf = [r for r in records if r.lower().startswith("v=spf1")]
    if not spf:
        return {"verified": False, "reason": "no_spf_txt", "records": records}

    # Soft pass: any v=spf1. Harder pass if platform include is expected.
    if require_include:
        needle = require_include.lower().strip()
        joined = " ".join(spf).lower()
        if needle and needle not in joined and f"include:{needle}" not in joined:
            # Still accept generic SPF so custom domains can use their own ESP include
            return {
                "verified": True,
                "reason": "spf_txt_found_without_platform_include",
                "records": spf,
                "warning": f"SPF present but does not include '{needle}'",
            }
    return {"verified": True, "reason": "spf_txt_found", "records": spf}


def check_dkim(domain: str, selector: str = "default") -> dict[str, Any]:
    domain = (domain or "").strip().lower().rstrip(".")
    selector = (selector or "default").strip() or "default"
    if not domain:
        return {"verified": False, "reason": "empty_domain", "records": []}
    name = f"{selector}._domainkey.{domain}"
    records = _lookup_txt(name)
    dkim = [
        r
        for r in records
        if "v=DKIM1" in r.replace(" ", "").upper() or "p=" in r.lower()
    ]
    if not dkim and records:
        dkim = records
    if not dkim:
        return {
            "verified": False,
            "reason": "no_dkim_txt",
            "lookup": name,
            "records": records,
        }
    return {
        "verified": True,
        "reason": "dkim_txt_found",
        "lookup": name,
        "records": dkim[:3],
        "selector": selector,
    }


def check_dkim_multi(domain: str, selectors: Optional[list[str]] = None) -> dict[str, Any]:
    """Try common selectors until one verifies (Resend/Google/etc.)."""
    default = "default"
    try:
        from app.core.config import get_settings
        default = getattr(get_settings(), "DKIM_SELECTOR", None) or "default"
    except Exception:
        pass
    candidates = selectors or [
        default,
        "resend",
        "google",
        "selector1",
        "selector2",
        "s1",
        "s2",
        "k1",
        "default",
    ]
    # de-dupe preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for s in candidates:
        s = (s or "").strip()
        if s and s not in seen:
            seen.add(s)
            ordered.append(s)

    last: dict[str, Any] = {"verified": False, "reason": "no_dkim_txt", "records": []}
    for sel in ordered:
        result = check_dkim(domain, selector=sel)
        if result.get("verified"):
            return result
        last = result
    return last


def check_dmarc(domain: str) -> dict[str, Any]:
    """
    DMARC is recommended for deliverability/trust.
    Stage 1: presence of a v=DMARC1 record at _dmarc.<domain> is enough to mark true.
    Policy p=none is accepted (monitoring); enforce is not required for can_send.
    """
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain:
        return {"verified": False, "reason": "empty_domain", "records": []}
    name = f"_dmarc.{domain}"
    records = _lookup_txt(name)
    dmarc = [r for r in records if "v=dmarc1" in r.lower().replace(" ", "")]
    if not dmarc:
        return {
            "verified": False,
            "reason": "no_dmarc_txt",
            "lookup": name,
            "records": records,
        }
    return {
        "verified": True,
        "reason": "dmarc_txt_found",
        "lookup": name,
        "records": dmarc[:2],
    }


def verify_domain_dns(
    domain: str,
    *,
    dkim_selector: str = "default",
    require_spf_include: Optional[str] = None,
) -> dict[str, Any]:
    include = require_spf_include
    if include is None:
        try:
            from app.core.config import get_settings
            root = (getattr(get_settings(), "ESP_PLATFORM_SENDING_ROOT_DOMAIN", "") or "").strip()
            include = root or None
        except Exception:
            include = None

    spf = check_spf(domain, require_include=include)
    # Prefer explicit selector first, then multi-fallback
    dkim = check_dkim(domain, selector=dkim_selector)
    if not dkim.get("verified"):
        dkim = check_dkim_multi(domain, selectors=[dkim_selector])
    dmarc = check_dmarc(domain)

    return {
        "domain": domain,
        "spf_verified": bool(spf.get("verified")),
        "dkim_verified": bool(dkim.get("verified")),
        "dmarc_verified": bool(dmarc.get("verified")),
        "spf": spf,
        "dkim": dkim,
        "dmarc": dmarc,
        # can_send still requires SPF+DKIM; DMARC is advisory in Stage 1
        "trust_ready": bool(spf.get("verified") and dkim.get("verified")),
    }
