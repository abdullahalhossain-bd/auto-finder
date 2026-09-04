"""GET /jobs/{id} — poll async work."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models.job import Job

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobRead(BaseModel):
    id: UUID
    type: str
    status: str
    celery_task_id: str | None = None
    result: dict | None = None
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    job = await db.get(Job, job_id)
    if job is None or job.organization_id != current.organization_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Job not found"}},
        )
    return JobRead(
        id=job.id,
        type=job.type,
        status=job.status,
        celery_task_id=job.celery_task_id,
        result=job.result,
        error=job.error,
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )
