"""SSRF guard unit tests — no network required for blocked cases."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.security.safe_fetch import (  # noqa: E402
    SafeFetchError,
    resolve_and_validate_host,
    safe_fetch,
    validate_url_for_fetch,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.0.0.1:80/",
        "http://localhost/",
        "http://[::1]/",
        "http://0.0.0.0/",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/",
        "http://10.0.0.5/admin",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "file:///etc/passwd",
        "ftp://example.com/",
        "http://user:pass@example.com/",
        "http://example.com:22/",
    ],
)
def test_validate_blocks_dangerous_urls(url):
    with pytest.raises(SafeFetchError):
        validate_url_for_fetch(url)


def test_validate_allows_public_hostname_shape():
    # Only validates structure + DNS; mock DNS to public IP
    with patch("app.security.safe_fetch.socket.getaddrinfo") as gai:
        gai.return_value = [
            (None, None, None, None, ("93.184.216.34", 0)),  # example.com public
        ]
        out = validate_url_for_fetch("https://example.com/path")
        assert out.startswith("https://example.com")


def test_private_dns_resolution_blocked():
    with patch("app.security.safe_fetch.socket.getaddrinfo") as gai:
        gai.return_value = [
            (None, None, None, None, ("10.1.2.3", 0)),
        ]
        with pytest.raises(SafeFetchError) as ei:
            resolve_and_validate_host("evil.internal")
        assert ei.value.code == "BLOCKED_IP"


def test_redirect_to_metadata_blocked():
    """Post-redirect check: first hop public, Location → 169.254.169.254."""
    first = MagicMock()
    first.status_code = 302
    first.headers = {"location": "http://169.254.169.254/latest/meta-data/"}

    with patch("app.security.safe_fetch.socket.getaddrinfo") as gai:
        gai.return_value = [
            (None, None, None, None, ("93.184.216.34", 0)),
        ]
        with patch("httpx.Client") as Client:
            client_inst = MagicMock()
            Client.return_value.__enter__.return_value = client_inst
            client_inst.request.return_value = first
            with pytest.raises(SafeFetchError) as ei:
                safe_fetch("https://example.com/start")
            assert ei.value.code in ("BLOCKED_IP", "BLOCKED_HOST", "INVALID_HOST")


def test_too_many_redirects():
    hop = MagicMock()
    hop.status_code = 302
    hop.headers = {"location": "https://example.com/next"}

    with patch("app.security.safe_fetch.socket.getaddrinfo") as gai:
        gai.return_value = [
            (None, None, None, None, ("93.184.216.34", 0)),
        ]
        with patch("httpx.Client") as Client:
            client_inst = MagicMock()
            Client.return_value.__enter__.return_value = client_inst
            client_inst.request.return_value = hop
            with pytest.raises(SafeFetchError) as ei:
                safe_fetch("https://example.com/a", max_redirects=2)
            assert ei.value.code == "TOO_MANY_REDIRECTS"
