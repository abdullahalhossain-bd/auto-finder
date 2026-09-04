"""Follow-up schedule API — max 1 per sent message; free template path."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models.followup import Followup
from app.services.followup_service import FollowupError, cancel_followup, schedule_followup

router = APIRouter(tags=["followups"])


class ScheduleFollowupRequest(BaseModel):
    delay_days: int = Field(3, ge=1, le=30)
    scheduled_at: Optional[datetime] = None


class FollowupRead(BaseModel):
    id: UUID
    message_id: UUID
    lead_id: UUID
    status: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.post(
    "/messages/{message_id}/followup",
    response_model=FollowupRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_followup(
    message_id: UUID,
    body: ScheduleFollowupRequest,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    try:
        row = await schedule_followup(
            db,
            organization_id=current.organization_id,
            message_id=message_id,
            delay_days=body.delay_days,
            scheduled_at=body.scheduled_at,
        )
    except FollowupError as exc:
        code = 404 if exc.code == "NOT_FOUND" else 409 if exc.code in ("ALREADY_EXISTS", "INVALID_STATUS", "LEAD_CLOSED") else 422
        raise HTTPException(
            status_code=code,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc
    return FollowupRead.model_validate(row)


@router.get("/messages/{message_id}/followup", response_model=FollowupRead | dict)
async def get_followup_for_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    row = (
        await db.execute(
            select(Followup).where(
                Followup.message_id == message_id,
                Followup.organization_id == current.organization_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return {"scheduled": False}
    return FollowupRead.model_validate(row)


@router.delete("/followups/{followup_id}", response_model=FollowupRead)
async def delete_followup(
    followup_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    try:
        row = await cancel_followup(
            db, organization_id=current.organization_id, followup_id=followup_id
        )
    except FollowupError as exc:
        code = 404 if exc.code == "NOT_FOUND" else 409
        raise HTTPException(
            status_code=code,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc
    return FollowupRead.model_validate(row)


@router.post("/followups/process-due", response_model=dict)
async def trigger_process_due(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """
    Manual trigger (dev / free ops). Enqueues Celery sweep; falls back to inline if broker down.
    """
    try:
        from app.workers.tasks import process_due_followups_task

        async_result = process_due_followups_task.delay()
        return {"queued": True, "task_id": async_result.id}
    except Exception:
        from app.core.sync_db import get_sync_session
        from app.services.followup_service import process_due_followups_sync

        session = get_sync_session()
        try:
            result = process_due_followups_sync(session)
            return {"queued": False, "inline": True, **result}
        finally:
            session.close()
