"""Celery application setup for background workers."""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_sales_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=True,
    # Global retry defaults (per-task overrides still apply)
    task_default_retry_delay=15,
    task_annotations={
        "*": {
            "max_retries": 3,
        }
    },
    # Prefer fair scheduling under load
    worker_prefetch_multiplier=1,
    # Visibility: don't hide failures
    task_eager_propagates=True,
)

# Free periodic processing (celery beat). No paid services.
celery_app.conf.beat_schedule = {
    "followups-process-due-every-5-min": {
        "task": "followups.process_due",
        "schedule": 300.0,
    },
    "purge-soft-deleted-daily": {
        "task": "maintenance.purge_soft_deleted",
        "schedule": 86400.0,
        "kwargs": {"older_than_days": 30},
    },
}
