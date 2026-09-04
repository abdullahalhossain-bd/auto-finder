"""
Celery retry helpers — exponential backoff + jitter (no paid broker features required).

Policy:
- Transient errors (network, timeout, 5xx, DB disconnect) → retry
- Permanent / business blocks (not found, suppressed, invalid state) → do NOT retry
- Backoff: base * 2^attempt + jitter, capped
"""
from __future__ import annotations

import random
from typing import Optional, Type

# Exceptions that should never be retried (caller may still catch and return)
NON_RETRYABLE_NAMES = {
    "SendBlockedError",  # depends on code — handled by caller
    "FollowupError",
    "PlanLimitExceeded",
    "BillingError",
    "SendingIdentityError",
    "SafeFetchError",
}


def retry_countdown(
    retries: int,
    *,
    base: int = 15,
    factor: float = 2.0,
    max_countdown: int = 600,
    jitter: float = 0.25,
) -> int:
    """
    retries = current attempt index (0 after first failure).
    Example: base=15 → ~15s, 30s, 60s, 120s ... + jitter, capped at max_countdown.
    """
    delay = float(base) * (factor ** max(0, int(retries)))
    delay = min(delay, float(max_countdown))
    if jitter > 0:
        spread = delay * jitter
        delay = delay + random.uniform(-spread, spread)
    return max(1, int(delay))


def is_retryable_exception(exc: BaseException) -> bool:
    """Heuristic: network / timeout / 5xx-ish → retry; ValueError business → no."""
    name = type(exc).__name__
    if name in NON_RETRYABLE_NAMES:
        return False
    # Common transient
    transient_types = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    if isinstance(exc, transient_types):
        return True
    # httpx / requests style
    mod = type(exc).__module__ or ""
    if "httpx" in mod or "urllib" in mod or "requests" in mod:
        return True
    if "timeout" in str(exc).lower() or "temporar" in str(exc).lower():
        return True
    if "connection" in str(exc).lower() and "refused" in str(exc).lower():
        return True
    # Default: retry unknown operational failures once policy allows
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return False
    return True


def retry_or_raise(task_self, exc: BaseException, *, base: int = 15, max_countdown: int = 600):
    """
    Call from `except` block of a bind=True task.
    Raises self.retry(...) or re-raises if max retries exceeded / non-retryable.
    """
    if not is_retryable_exception(exc):
        raise exc
    retries = int(getattr(getattr(task_self, "request", None), "retries", 0) or 0)
    countdown = retry_countdown(retries, base=base, max_countdown=max_countdown)
    raise task_self.retry(exc=exc, countdown=countdown)
