"""
Structured logging for AI Sales Agent.

Design:
- JSON lines on stdout in production (log shippers / CloudWatch / Loki)
- Human-readable lines in development
- ContextVars carry request_id / organization_id / user_id / job_id onto every record
- Optional Sentry when SENTRY_DSN is set

Usage:
    from app.core.logging_config import get_logger, bind_context, clear_context, log_event

    logger = get_logger(__name__)
    logger.info("campaign.started", extra={"campaign_id": str(cid)})
    # or
    log_event("campaign.started", campaign_id=str(cid), organization_id=str(oid))
"""
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, MutableMapping, Optional

# --- request / job context (propagates across await boundaries) ---
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_organization_id: ContextVar[Optional[str]] = ContextVar("organization_id", default=None)
_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_job_id: ContextVar[Optional[str]] = ContextVar("job_id", default=None)
_job_type: ContextVar[Optional[str]] = ContextVar("job_type", default=None)

_SERVICE_NAME = "ai-sales-agent"
_APP_ENV = "development"


def bind_context(
    *,
    request_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
    job_type: Optional[str] = None,
) -> None:
    """Attach correlation fields for the current async/task context."""
    if request_id is not None:
        _request_id.set(str(request_id))
    if organization_id is not None:
        _organization_id.set(str(organization_id))
    if user_id is not None:
        _user_id.set(str(user_id))
    if job_id is not None:
        _job_id.set(str(job_id))
    if job_type is not None:
        _job_type.set(str(job_type))


def clear_context() -> None:
    _request_id.set(None)
    _organization_id.set(None)
    _user_id.set(None)
    _job_id.set(None)
    _job_type.set(None)


def get_context() -> dict[str, str]:
    out: dict[str, str] = {}
    if _request_id.get():
        out["request_id"] = _request_id.get()  # type: ignore[assignment]
    if _organization_id.get():
        out["organization_id"] = _organization_id.get()  # type: ignore[assignment]
    if _user_id.get():
        out["user_id"] = _user_id.get()  # type: ignore[assignment]
    if _job_id.get():
        out["job_id"] = _job_id.get()  # type: ignore[assignment]
    if _job_type.get():
        out["job_type"] = _job_type.get()  # type: ignore[assignment]
    return out


class ContextFilter(logging.Filter):
    """Inject ContextVar values + service metadata onto every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = _SERVICE_NAME  # type: ignore[attr-defined]
        record.env = _APP_ENV  # type: ignore[attr-defined]
        ctx = get_context()
        for key in ("request_id", "organization_id", "user_id", "job_id", "job_type"):
            # Prefer explicit extra= on the call; fall back to context
            if not getattr(record, key, None):
                setattr(record, key, ctx.get(key))
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line — safe for aggregation."""

    RESERVED = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "service": getattr(record, "service", _SERVICE_NAME),
            "env": getattr(record, "env", _APP_ENV),
        }
        for key in ("request_id", "organization_id", "user_id", "job_id", "job_type"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val

        # Any other non-reserved attributes from logger.info(..., extra={...})
        for key, val in record.__dict__.items():
            if key in self.RESERVED or key in payload:
                continue
            if key.startswith("_"):
                continue
            if val is None:
                continue
            try:
                json.dumps(val)
                payload[key] = val
            except (TypeError, ValueError):
                payload[key] = str(val)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class DevFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx_bits = []
        for key in ("request_id", "organization_id", "job_id"):
            val = getattr(record, key, None)
            if val:
                ctx_bits.append(f"{key}={val}")
        ctx = f" [{', '.join(ctx_bits)}]" if ctx_bits else ""
        base = f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} {record.levelname:5s} [{record.name}]{ctx} {record.getMessage()}"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def setup_logging(
    level: str = "INFO",
    *,
    json_logs: bool = True,
    app_env: str = "development",
    service_name: str = "ai-sales-agent",
) -> None:
    global _APP_ENV, _SERVICE_NAME
    _APP_ENV = app_env
    _SERVICE_NAME = service_name

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(DevFormatter())
    root.addHandler(handler)

    # Library noise
    for name in ("httpx", "httpcore", "asyncio", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("celery").setLevel(logging.INFO)

    _maybe_init_sentry()


def _maybe_init_sentry() -> None:
    try:
        from app.core.config import get_settings

        settings = get_settings()
    except Exception:
        return
    dsn = (getattr(settings, "SENTRY_DSN", "") or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            environment=getattr(settings, "APP_ENV", "development"),
            traces_sample_rate=0.1 if getattr(settings, "APP_ENV", "") == "production" else 0.0,
            send_default_pii=False,
        )
        logging.getLogger(__name__).info("sentry.initialized", extra={"event": "sentry.initialized"})
    except Exception:
        logging.getLogger(__name__).debug("sentry.init_skipped", exc_info=True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(
    event: str,
    *,
    level: int = logging.INFO,
    logger_name: str = "app.events",
    **fields: Any,
) -> None:
    """
    Emit a structured event. `event` becomes both msg and an `event` field.

    Example:
        log_event("message.approved", message_id=str(mid), organization_id=str(oid))
    """
    logger = logging.getLogger(logger_name)
    extra: MutableMapping[str, Any] = {"event": event}
    for k, v in fields.items():
        if v is not None:
            extra[k] = v if not hasattr(v, "hex") else str(v)
    logger.log(level, event, extra=extra)
