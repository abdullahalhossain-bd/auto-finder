"""DNS verify helpers — offline shape tests."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.dns_verify import (  # noqa: E402
    check_spf,
    check_dkim,
    check_dmarc,
    verify_domain_dns,
)


def test_empty_domain():
    assert check_spf("")["verified"] is False
    assert check_dkim("")["verified"] is False
    assert check_dmarc("")["verified"] is False


def test_spf_found():
    with patch(
        "app.services.dns_verify._lookup_txt",
        return_value=["v=spf1 include:_spf.google.com ~all"],
    ):
        r = check_spf("example.com")
        assert r["verified"] is True


def test_dkim_found():
    with patch(
        "app.services.dns_verify._lookup_txt",
        return_value=["v=DKIM1; k=rsa; p=abc"],
    ):
        r = check_dkim("example.com", selector="default")
        assert r["verified"] is True


def test_dmarc_found():
    with patch(
        "app.services.dns_verify._lookup_txt",
        return_value=["v=DMARC1; p=none;"],
    ):
        r = check_dmarc("example.com")
        assert r["verified"] is True


def test_verify_domain_combines():
    with patch("app.services.dns_verify._lookup_txt", return_value=[]):
        r = verify_domain_dns("example.com")
        assert r["spf_verified"] is False
        assert r["dkim_verified"] is False
        assert r["dmarc_verified"] is False
        assert r["trust_ready"] is False


def test_verify_domain_trust_ready():
    def fake_lookup(name: str):
        if name.startswith("_dmarc."):
            return ["v=DMARC1; p=quarantine;"]
        if "._domainkey." in name:
            return ["v=DKIM1; k=rsa; p=abc"]
        return ["v=spf1 include:_spf.example ~all"]

    with patch("app.services.dns_verify._lookup_txt", side_effect=fake_lookup):
        r = verify_domain_dns("example.com")
        assert r["spf_verified"] is True
        assert r["dkim_verified"] is True
        assert r["dmarc_verified"] is True
        assert r["trust_ready"] is True
