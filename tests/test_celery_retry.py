"""Celery retry backoff unit tests — no broker required."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.workers.retry import is_retryable_exception, retry_countdown  # noqa: E402


def test_countdown_grows_and_caps():
    d0 = retry_countdown(0, base=10, factor=2.0, max_countdown=100, jitter=0)
    d1 = retry_countdown(1, base=10, factor=2.0, max_countdown=100, jitter=0)
    d2 = retry_countdown(2, base=10, factor=2.0, max_countdown=100, jitter=0)
    d9 = retry_countdown(9, base=10, factor=2.0, max_countdown=100, jitter=0)
    assert d0 == 10
    assert d1 == 20
    assert d2 == 40
    assert d9 == 100  # capped


def test_value_error_not_retryable():
    assert is_retryable_exception(ValueError("bad")) is False


def test_connection_error_retryable():
    assert is_retryable_exception(ConnectionError("down")) is True


def test_timeout_retryable():
    assert is_retryable_exception(TimeoutError("slow")) is True
