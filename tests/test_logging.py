"""Structured logging unit tests — no DB."""
import json
import logging
import sys
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.logging_config import (  # noqa: E402
    ContextFilter,
    JsonFormatter,
    bind_context,
    clear_context,
    get_context,
    log_event,
    setup_logging,
)


def test_bind_and_clear_context():
    clear_context()
    bind_context(request_id="req-1", organization_id="org-1", user_id="u-1")
    ctx = get_context()
    assert ctx["request_id"] == "req-1"
    assert ctx["organization_id"] == "org-1"
    clear_context()
    assert get_context() == {}


def test_json_formatter_includes_context_and_extra():
    clear_context()
    bind_context(request_id="rid-99", job_id="job-1")
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    record.request_id = "rid-99"  # type: ignore[attr-defined]
    record.job_id = "job-1"  # type: ignore[attr-defined]
    record.campaign_id = "c-1"  # type: ignore[attr-defined]
    record.service = "ai-sales-agent"  # type: ignore[attr-defined]
    record.env = "test"  # type: ignore[attr-defined]
    out = JsonFormatter().format(record)
    data = json.loads(out)
    assert data["msg"] == "hello world"
    assert data["request_id"] == "rid-99"
    assert data["job_id"] == "job-1"
    assert data["campaign_id"] == "c-1"
    assert data["level"] == "INFO"
    assert "ts" in data
    clear_context()


def test_log_event_emits_event_field():
    clear_context()
    bind_context(organization_id="o-1")
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(ContextFilter())
    handler.setFormatter(JsonFormatter())
    lg = logging.getLogger("app.events")
    lg.handlers.clear()
    lg.addHandler(handler)
    lg.setLevel(logging.INFO)
    lg.propagate = False

    log_event("message.approved", message_id="m-1", organization_id="o-1")

    lines = [ln for ln in stream.getvalue().splitlines() if ln.strip()]
    assert lines, "expected at least one log line"
    data = json.loads(lines[-1])
    assert data["msg"] == "message.approved"
    assert data["event"] == "message.approved"
    assert data["message_id"] == "m-1"
    assert data.get("organization_id") == "o-1"
    lg.handlers.clear()
    clear_context()


def test_setup_logging_json_mode_smoke():
    setup_logging(level="INFO", json_logs=True, app_env="test")
    clear_context()
