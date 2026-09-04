"""
SSRF-safe HTTP fetch (CODING_STANDARDS).

Rules:
- Only http/https
- Resolve hostname BEFORE connect; reject private/link-local/loopback/metadata IPs
- After each redirect, re-validate final URL host IP (post-redirect check)
- Cap redirects, response size, timeout
- No credentials in URL
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Optional, Sequence, Set
from urllib.parse import urlparse

import httpx

# Cloud metadata & common SSRF targets
BLOCKED_HOSTNAMES: Set[str] = {
    "metadata.google.internal",
    "metadata.google.com",
    "169.254.169.254",
    "metadata",
    "localhost",
}


class SafeFetchError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        return True
    if ip.is_multicast or ip.is_unspecified:
        return True
    # IPv6 unique local
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return _is_blocked_ip(ip.ipv4_mapped)
    # AWS/GCP metadata often 169.254.169.254 (link-local — already caught)
    return False


def resolve_and_validate_host(hostname: str) -> list[str]:
    """DNS resolve and ensure no blocked IPs. Returns resolved address strings."""
    host = (hostname or "").strip().lower().rstrip(".")
    if not host:
        raise SafeFetchError("INVALID_HOST", "Empty hostname")
    if host in BLOCKED_HOSTNAMES:
        raise SafeFetchError("BLOCKED_HOST", f"Hostname not allowed: {host}")
    if host.endswith(".localhost") or host.endswith(".local"):
        raise SafeFetchError("BLOCKED_HOST", f"Hostname not allowed: {host}")

    # Literal IP in hostname
    try:
        ip = ipaddress.ip_address(host)
        if _is_blocked_ip(ip):
            raise SafeFetchError("BLOCKED_IP", f"IP address not allowed: {host}")
        return [host]
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SafeFetchError("DNS_FAILED", f"DNS resolution failed for {host}: {exc}") from exc

    resolved: list[str] = []
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise SafeFetchError(
                "BLOCKED_IP",
                f"Hostname {host} resolves to blocked address {addr}",
            )
        resolved.append(addr)
    if not resolved:
        raise SafeFetchError("DNS_FAILED", f"No usable addresses for {host}")
    return resolved


def validate_url_for_fetch(url: str) -> str:
    """
    Validate URL scheme/host before any network I/O.
    Returns normalized URL string.
    """
    if not url or not isinstance(url, str):
        raise SafeFetchError("INVALID_URL", "URL is required")
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SafeFetchError("INVALID_SCHEME", "Only http and https are allowed")
    if not parsed.hostname:
        raise SafeFetchError("INVALID_HOST", "URL must include a hostname")
    if parsed.username or parsed.password:
        raise SafeFetchError("CREDENTIALS_FORBIDDEN", "Userinfo in URL is not allowed")
    # Port sanity
    if parsed.port is not None and parsed.port not in (80, 443, 8080, 8443):
        # Allow common web ports only
        raise SafeFetchError("BLOCKED_PORT", f"Port {parsed.port} is not allowed")

    resolve_and_validate_host(parsed.hostname)
    return url


class _RedirectGuard(httpx.Auth):
    """Unused — we disable auto-follow and walk redirects manually."""
    pass


def safe_fetch(
    url: str,
    *,
    method: str = "GET",
    timeout: float = 10.0,
    max_bytes: int = 5_242_880,
    max_redirects: int = 5,
    headers: Optional[dict] = None,
) -> httpx.Response:
    """
    Synchronous SSRF-safe fetch with pre- and post-redirect IP checks.
    """
    current = validate_url_for_fetch(url)
    hdrs = {
        "User-Agent": "AISalesAgent-SafeFetch/1.0",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }
    if headers:
        hdrs.update(headers)

    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        max_redirects=0,
    ) as client:
        for _ in range(max_redirects + 1):
            validate_url_for_fetch(current)
            resp = client.request(method, current, headers=hdrs)

            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("location")
                if not loc:
                    raise SafeFetchError("BAD_REDIRECT", "Redirect without Location")
                # Relative redirects
                next_url = str(httpx.URL(current).join(loc))
                # Re-validate target (post-redirect)
                current = validate_url_for_fetch(next_url)
                method = "GET" if resp.status_code in (301, 302, 303) else method
                continue

            # Success / error body — enforce size
            content = resp.content
            if len(content) > max_bytes:
                raise SafeFetchError(
                    "RESPONSE_TOO_LARGE",
                    f"Response exceeds {max_bytes} bytes",
                )
            # Final URL host already validated on last hop
            return resp

        raise SafeFetchError("TOO_MANY_REDIRECTS", f"Exceeded {max_redirects} redirects")


async def safe_fetch_async(
    url: str,
    *,
    method: str = "GET",
    timeout: float = 10.0,
    max_bytes: int = 5_242_880,
    max_redirects: int = 5,
    headers: Optional[dict] = None,
) -> httpx.Response:
    """Async variant with the same SSRF controls."""
    current = validate_url_for_fetch(url)
    hdrs = {
        "User-Agent": "AISalesAgent-SafeFetch/1.0",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }
    if headers:
        hdrs.update(headers)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        max_redirects=0,
    ) as client:
        for _ in range(max_redirects + 1):
            validate_url_for_fetch(current)
            resp = await client.request(method, current, headers=hdrs)

            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("location")
                if not loc:
                    raise SafeFetchError("BAD_REDIRECT", "Redirect without Location")
                next_url = str(httpx.URL(current).join(loc))
                current = validate_url_for_fetch(next_url)
                method = "GET" if resp.status_code in (301, 302, 303) else method
                continue

            content = resp.content
            if len(content) > max_bytes:
                raise SafeFetchError(
                    "RESPONSE_TOO_LARGE",
                    f"Response exceeds {max_bytes} bytes",
                )
            return resp

        raise SafeFetchError("TOO_MANY_REDIRECTS", f"Exceeded {max_redirects} redirects")
