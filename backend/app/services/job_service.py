"""Sync job row status from Celery workers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _find(session: Session, *, celery_task_id: Optional[str] = None, job_id: Optional[UUID] = None) -> Optional[Job]:
    if job_id:
        return session.get(Job, job_id)
    if celery_task_id:
        return (
            session.execute(select(Job).where(Job.celery_task_id == celery_task_id))
            .scalars()
            .first()
        )
    return None


def mark_job_running(
    session: Session,
    *,
    celery_task_id: Optional[str] = None,
    job_id: Optional[UUID] = None,
) -> Optional[Job]:
    job = _find(session, celery_task_id=celery_task_id, job_id=job_id)
    if job is None:
        return None
    job.status = "running"
    if job.started_at is None:
        job.started_at = _now()
    session.commit()
    return job


def mark_job_completed(
    session: Session,
    *,
    celery_task_id: Optional[str] = None,
    job_id: Optional[UUID] = None,
    result: Optional[dict[str, Any]] = None,
) -> Optional[Job]:
    job = _find(session, celery_task_id=celery_task_id, job_id=job_id)
    if job is None:
        return None
    job.status = "completed"
    job.result = result
    job.error = None
    job.finished_at = _now()
    session.commit()
    return job


def mark_job_failed(
    session: Session,
    *,
    celery_task_id: Optional[str] = None,
    job_id: Optional[UUID] = None,
    error: str,
) -> Optional[Job]:
    job = _find(session, celery_task_id=celery_task_id, job_id=job_id)
    if job is None:
        return None
    job.status = "failed"
    job.error = (error or "")[:2000]
    job.finished_at = _now()
    session.commit()
    return job
