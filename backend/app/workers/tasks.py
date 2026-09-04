"""
Celery background tasks with unified retry policy.

Retry: exponential backoff + jitter (app.workers.retry).
acks_late + reject_on_worker_lost → task re-queued if worker dies mid-flight.
Idempotent where possible (discovery skips existing leads; send re-checks gates).
"""
from __future__ import annotations

from app.core.celery_app import celery_app
from app.core.logging_config import bind_context, clear_context, get_logger, log_event
from app.workers.retry import retry_countdown, retry_or_raise

logger = get_logger(__name__)


def _bind_task(self, *, organization_id: str | None = None, job_type: str) -> None:
    task_id = getattr(getattr(self, "request", None), "id", None)
    bind_context(
        job_id=str(task_id) if task_id else None,
        job_type=job_type,
        organization_id=organization_id,
    )


def _celery_id(self) -> str:
    return str(getattr(getattr(self, "request", None), "id", "") or "")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
@celery_app.task(
    name="discovery.run_campaign",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=300,
    time_limit=360,
)
def run_campaign_discovery(self, campaign_id: str, organization_id: str | None = None):
    """Background discovery + website audit + scoring. Safe to retry (skips existing leads)."""
    from uuid import UUID

    from app.core.sync_db import get_sync_session
    from app.models.campaign import Campaign
    from app.services.discovery_pipeline import run_discovery_pipeline_sync
    from app.services.job_service import mark_job_completed, mark_job_failed, mark_job_running

    _bind_task(self, organization_id=organization_id, job_type="discovery.run_campaign")
    log_event(
        "discovery.started",
        campaign_id=campaign_id,
        organization_id=organization_id,
        attempt=self.request.retries,
    )
    session = get_sync_session()
    celery_id = _celery_id(self)
    try:
        mark_job_running(session, celery_task_id=celery_id)
    except Exception:
        pass

    try:
        cid = UUID(campaign_id)
        campaign = session.get(Campaign, cid)
        if campaign is None:
            log_event("discovery.failed", level=40, campaign_id=campaign_id, reason="not_found")
            try:
                mark_job_failed(session, celery_task_id=celery_id, error="not_found")
            except Exception:
                pass
            return {"error": "not_found", "campaign_id": campaign_id}
        if organization_id and str(campaign.organization_id) != str(organization_id):
            log_event("discovery.failed", level=40, campaign_id=campaign_id, reason="org_mismatch")
            try:
                mark_job_failed(session, celery_task_id=celery_id, error="org_mismatch")
            except Exception:
                pass
            return {"error": "org_mismatch", "campaign_id": campaign_id}
        if campaign.status == "cancelled":
            return {"error": "cancelled", "campaign_id": campaign_id}

        bind_context(organization_id=str(campaign.organization_id))
        result = run_discovery_pipeline_sync(session, cid)

        # run_discovery_pipeline_sync returns (never raises) for expected,
        # non-retryable business/user errors — e.g. missing city/business_type,
        # campaign not found. Celery itself sees this as a normal return
        # (correct — retrying won't fix a validation error), but our own
        # Job row must NOT be marked "completed" for one of these, or the
        # frontend will show success on a campaign that produced nothing.
        is_business_error = isinstance(result, dict) and bool(result.get("error"))
        if is_business_error:
            log_event(
                "discovery.failed",
                level=30,
                campaign_id=campaign_id,
                reason=result.get("error"),
                # NOTE: don't call this field "message" — Python logging's
                # LogRecord already reserves that key in `extra` and raises
                # KeyError("Attempt to overwrite 'message'...") at emit time.
                detail=result.get("message"),
            )
            try:
                mark_job_failed(
                    session,
                    celery_task_id=celery_id,
                    error=result.get("message") or str(result.get("error")),
                )
            except Exception:
                pass
        else:
            log_event(
                "discovery.completed",
                campaign_id=campaign_id,
                total_found=result.get("total_found"),
                qualified=result.get("qualified"),
                status=result.get("status"),
            )
            try:
                mark_job_completed(
                    session,
                    celery_task_id=celery_id,
                    result=result if isinstance(result, dict) else {"ok": True},
                )
            except Exception:
                pass
        return result
    except Exception as exc:
        log_event(
            "discovery.failed",
            level=40,
            campaign_id=campaign_id,
            error=str(exc)[:300],
            attempt=self.request.retries,
            next_countdown=retry_countdown(self.request.retries, base=30),
        )
        logger.exception("discovery.run_campaign failed campaign_id=%s", campaign_id)
        try:
            mark_job_failed(session, celery_task_id=celery_id, error=str(exc)[:500])
        except Exception:
            pass
        try:
            campaign = session.get(Campaign, UUID(campaign_id))
            if campaign and campaign.status in ("discovering", "scoring", "running"):
                # Only mark failed on final attempt
                if self.request.retries >= self.max_retries:
                    campaign.status = "failed"
                    session.commit()
        except Exception:
            session.rollback()
        retry_or_raise(self, exc, base=30, max_countdown=900)
    finally:
        session.close()
        clear_context()


# ---------------------------------------------------------------------------
# Outreach send
# ---------------------------------------------------------------------------
@celery_app.task(
    name="outreach.send_message",
    bind=True,
    max_retries=5,
    default_retry_delay=20,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=60,
    time_limit=90,
)
def send_message_task(self, message_id: str):
    """
    Authoritative send path after human approval.
    Permanent blocks (suppressed, not approved, caps) → no retry.
    Transient ESP/network → exponential retry.
    """
    from uuid import UUID

    from app.core.sync_db import get_sync_session
    from app.services.job_service import mark_job_completed, mark_job_failed
    from app.services.outreach_service import SendBlockedError, send_approved_message

    _bind_task(self, job_type="outreach.send_message")
    log_event(
        "outreach.send_started",
        message_id=message_id,
        attempt=self.request.retries,
    )
    session = get_sync_session()
    celery_id = _celery_id(self)
    try:
        msg = send_approved_message(session, UUID(message_id))
        log_event(
            "outreach.send_completed",
            message_id=str(msg.id),
            status=msg.status,
            provider=msg.esp_provider,
            to_email=msg.to_email,
            esp_message_id=msg.esp_message_id,
        )
        try:
            mark_job_completed(
                session,
                celery_task_id=celery_id,
                result={"message_id": str(msg.id), "status": msg.status},
            )
        except Exception:
            pass
        return {
            "message_id": str(msg.id),
            "status": msg.status,
            "esp_message_id": msg.esp_message_id,
            "provider": msg.esp_provider,
            "to_email": msg.to_email,
        }
    except SendBlockedError as exc:
        log_event(
            "outreach.send_blocked",
            level=30,
            message_id=message_id,
            code=exc.code,
            reason=exc.message,
        )
        # Permanent business gates — do not retry
        permanent = {
            "NOT_APPROVED",
            "SUPPRESSED_CONTACT",
            "DAILY_CAP",
            "WEEKLY_CAP",
            "NO_RECIPIENT",
            "NOT_FOUND",
            "SENDING_IDENTITY_REQUIRED",
            "SENDING_IDENTITY_UNVERIFIED",
            "SENDING_PAUSED",
        }
        if exc.code in permanent:
            try:
                mark_job_failed(
                    session,
                    celery_task_id=celery_id,
                    error=f"{exc.code}: {exc.message}",
                )
            except Exception:
                pass
            return {
                "message_id": message_id,
                "blocked": True,
                "code": exc.code,
                "error": exc.message,
            }
        # ESP_FAILED and similar → retry
        log_event(
            "outreach.send_retry",
            message_id=message_id,
            code=exc.code,
            attempt=self.request.retries,
            countdown=retry_countdown(self.request.retries, base=20),
        )
        raise self.retry(
            exc=exc,
            countdown=retry_countdown(self.request.retries, base=20, max_countdown=600),
        )
    except Exception as exc:
        log_event(
            "outreach.send_failed",
            level=40,
            message_id=message_id,
            error=str(exc)[:300],
            attempt=self.request.retries,
        )
        logger.exception("Unexpected send failure for %s", message_id)
        if self.request.retries >= self.max_retries:
            try:
                mark_job_failed(session, celery_task_id=celery_id, error=str(exc)[:500])
            except Exception:
                pass
        retry_or_raise(self, exc, base=20, max_countdown=600)
    finally:
        session.close()
        clear_context()


# ---------------------------------------------------------------------------
# LLM generate
# ---------------------------------------------------------------------------
@celery_app.task(
    name="llm.generate_message",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=180,
    time_limit=240,
)
def generate_message_task(
    self,
    lead_id: str,
    organization_id: str,
    contact_id: str | None = None,
    service_offered: str | None = None,
    provider: str = "ollama",
):
    """Background personalization → Message(pending_approval). Template fallback is local."""
    from uuid import UUID

    from app.core.sync_db import get_sync_session
    from app.services.message_generation_service import generate_message_for_lead_sync

    _bind_task(self, organization_id=organization_id, job_type="llm.generate_message")
    log_event(
        "llm.generate_started",
        lead_id=lead_id,
        organization_id=organization_id,
        attempt=self.request.retries,
    )
    session = get_sync_session()
    try:
        msg = generate_message_for_lead_sync(
            session,
            lead_id=UUID(lead_id),
            organization_id=UUID(organization_id),
            contact_id=UUID(contact_id) if contact_id else None,
            service_offered=service_offered,
            provider=provider or "ollama",
        )
        meta = getattr(msg, "_generation_meta", {}) or {}
        log_event(
            "llm.generate_completed",
            lead_id=lead_id,
            message_id=str(msg.id),
            provider=meta.get("provider") or msg.generation_provider,
            used_fallback=meta.get("used_fallback"),
            latency_ms=meta.get("latency_ms"),
        )
        return {
            "message_id": str(msg.id),
            "lead_id": lead_id,
            "status": msg.status,
            "subject": msg.subject,
            "provider": meta.get("provider"),
            "used_fallback": meta.get("used_fallback"),
        }
    except Exception as exc:
        log_event(
            "llm.generate_failed",
            level=40,
            lead_id=lead_id,
            error=str(exc)[:300],
            attempt=self.request.retries,
        )
        logger.exception("llm.generate_message failed lead=%s", lead_id)
        retry_or_raise(self, exc, base=10, max_countdown=300)
    finally:
        session.close()
        clear_context()


# ---------------------------------------------------------------------------
# Follow-ups
# ---------------------------------------------------------------------------
@celery_app.task(
    name="followups.process_due",
    bind=True,
    max_retries=2,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=120,
    time_limit=180,
)
def process_due_followups_task(self):
    """Periodic: due follow-ups → pending_approval messages (template, free)."""
    from app.core.sync_db import get_sync_session
    from app.services.followup_service import process_due_followups_sync

    _bind_task(self, job_type="followups.process_due")
    log_event("followup.sweep_started", attempt=self.request.retries)
    session = get_sync_session()
    try:
        result = process_due_followups_sync(session, limit=50)
        log_event(
            "followup.sweep_completed",
            processed=result.get("processed"),
            skipped=result.get("skipped"),
            examined=result.get("examined"),
        )
        return result
    except Exception as exc:
        log_event("followup.sweep_failed", level=40, error=str(exc)[:300])
        logger.exception("followups.process_due failed")
        retry_or_raise(self, exc, base=30, max_countdown=300)
    finally:
        session.close()
        clear_context()


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------
@celery_app.task(
    name="maintenance.purge_soft_deleted",
    bind=True,
    max_retries=1,
    acks_late=True,
    soft_time_limit=600,
    time_limit=720,
)
def purge_soft_deleted_task(self, older_than_days: int = 30):
    """Hard-delete rows soft-deleted more than N days ago."""
    from app.core.sync_db import get_sync_session
    from app.services.soft_delete_service import hard_purge_sync

    _bind_task(self, job_type="maintenance.purge_soft_deleted")
    session = get_sync_session()
    try:
        result = hard_purge_sync(session, older_than_days=older_than_days)
        log_event("maintenance.purge_completed", **result)
        return result
    except Exception as exc:
        logger.exception("purge_soft_deleted failed")
        retry_or_raise(self, exc, base=60, max_countdown=600)
    finally:
        session.close()
        clear_context()