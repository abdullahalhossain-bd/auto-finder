"""
Rate limiter — Redis when available (multi-worker), in-process fallback.
Free stack: same Redis as Celery.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings


class SlidingWindowCounter:
    def __init__(self) -> None:
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str, limit: int, window_sec: float) -> Tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            q = self._events[key]
            cutoff = now - window_sec
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                return False, 0
            q.append(now)
            return True, max(0, limit - len(q))


_memory = SlidingWindowCounter()
_redis_client = None
_redis_failed = False


def _get_redis():
    global _redis_client, _redis_failed
    if _redis_failed:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis

        settings = get_settings()
        url = getattr(settings, "REDIS_URL", None) or getattr(
            settings, "CELERY_BROKER_URL", "redis://localhost:6379/0"
        )
        # Prefer dedicated REDIS_URL; broker may use /1
        if "CELERY" in (url or "") or url.endswith("/1") or url.endswith("/2"):
            url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        client = redis.Redis.from_url(url, socket_connect_timeout=0.5, decode_responses=True)
        client.ping()
        _redis_client = client
        return client
    except Exception:
        _redis_failed = True
        return None


def _redis_hit(key: str, limit: int, window_sec: int) -> Tuple[bool, int]:
    """Fixed window counter via INCR + EXPIRE (simple, multi-node safe)."""
    r = _get_redis()
    if r is None:
        return _memory.hit(key, limit, float(window_sec))
    try:
        bucket = int(time.time() // window_sec)
        rk = f"rl:{key}:{bucket}"
        count = r.incr(rk)
        if count == 1:
            r.expire(rk, window_sec + 1)
        remaining = max(0, limit - int(count))
        return int(count) <= limit, remaining
    except Exception:
        return _memory.hit(key, limit, float(window_sec))


_AUTH_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return await call_next(request)

        if request.url.path in (
            "/health",
            "/api/v1/legal/privacy",
            "/api/v1/legal/terms",
        ):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        path = request.url.path

        if path in _AUTH_PATHS:
            limit = int(getattr(settings, "RATE_LIMIT_AUTH_PER_MIN", 20))
            key = f"auth:{client}"
        else:
            limit = int(getattr(settings, "RATE_LIMIT_API_PER_MIN", 120))
            key = f"api:{client}:{path.split('/')[3] if path.startswith('/api/') else 'root'}"

        allowed, remaining = _redis_hit(key, limit=limit, window_sec=60)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please slow down and try again shortly.",
                    }
                },
                headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
