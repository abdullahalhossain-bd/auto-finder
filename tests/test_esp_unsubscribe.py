"""Unsubscribe injection is mandatory server-side."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.esp_client import (  # noqa: E402
    content_has_unsubscribe_link,
    ensure_unsubscribe_link,
)


def test_injects_when_missing():
    body = "Hello, we help with websites."
    out = ensure_unsubscribe_link(body, "https://example.com/api/v1/unsubscribe?token=abc")
    assert content_has_unsubscribe_link(out)
    assert "unsubscribe" in out.lower()


def test_does_not_duplicate_existing_link():
    body = "Hi\nhttps://example.com/unsubscribe?x=1\nBye"
    out = ensure_unsubscribe_link(body, "https://example.com/api/v1/unsubscribe?token=abc")
    assert out.count("unsubscribe") == 1
