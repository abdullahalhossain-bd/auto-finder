"""Bind request_id (and later user/org) into logging context for the request lifetime."""
from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_config import bind_context, clear_context, get_logger, log_event

logger = get_logger("app.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        bind_context(request_id=request_id)

        start = time.perf_counter()
        response: Response | None = None
        error: Exception | None = None
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error = exc
            raise
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            status_code = response.status_code if response is not None else 500

            # Pull auth context if deps already ran and stashed it
            org_id = getattr(request.state, "organization_id", None)
            user_id = getattr(request.state, "user_id", None)
            if org_id or user_id:
                bind_context(
                    organization_id=str(org_id) if org_id else None,
                    user_id=str(user_id) if user_id else None,
                )

            log_event(
                "http.request",
                logger_name="app.access",
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration_ms=duration_ms,
                client_ip=(request.client.host if request.client else None),
                user_agent=(request.headers.get("user-agent") or "")[:200] or None,
                error_type=type(error).__name__ if error else None,
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            clear_context()
