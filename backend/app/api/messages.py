"""
Message & Approval API.

CRITICAL RULE: No message can be sent without explicit human approval.
Approve → status=approved → enqueue outreach.send_message worker.
The worker re-checks status, suppression, caps, and unsubscribe injection.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.repositories.lead_repository import LeadRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.suppression_repository import SuppressionRepository
from app.schemas.message import MessageCreate, MessageRead, MessageUpdate
from app.core.logging_config import log_event
from app.services.audit_service import write_audit

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def create_message(
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Create a draft message for a lead (usually AI-generated). Always pending_approval."""
    lead_repo = LeadRepository(db)
    lead = await lead_repo.get_by_id(payload.lead_id, current.organization_id)
    if not lead:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Lead not found"}},
        )

    msg_repo = MessageRepository(db)
    message = await msg_repo.create(
        lead_id=payload.lead_id,
        content=payload.content,
        status="pending_approval",
        contact_id=payload.contact_id,
        subject=payload.subject,
    )
    return message


@router.get("/pending", response_model=list[MessageRead])
async def list_pending_approvals(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Approval Queue — messages waiting for human approval."""
    repo = MessageRepository(db)
    items, _ = await repo.list_pending_approval(
        current.organization_id, limit=limit, offset=offset
    )
    return items


@router.get("/{message_id}", response_model=MessageRead)
async def get_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    repo = MessageRepository(db)
    message = await repo.get_by_id(message_id, current.organization_id)
    if not message:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Message not found"}},
        )
    return message


@router.post("/{message_id}/approve", response_model=MessageRead)
async def approve_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """
    Explicit human approval.
    Sets status=approved, then enqueues the send worker.
    Actual delivery happens only inside the worker after re-checks.
    """
    repo = MessageRepository(db)
    message = await repo.get_by_id(message_id, current.organization_id)
    if not message:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Message not found"}},
        )
    if message.status not in ("pending_approval", "draft"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_STATE",
                    "message": f"Cannot approve message in status: {message.status}",
                }
            },
        )

    # Fast-fail: subscription + sending identity (worker still re-checks)
    from app.services.plan_limits import PlanLimitExceeded, assert_can_send_outbound
    from app.services.sending_identity_service import (
        SendingIdentityError,
        get_primary_identity,
    )

    try:
        await assert_can_send_outbound(db, current.organization_id)
    except PlanLimitExceeded as exc:
        raise HTTPException(
            status_code=402,
            detail={"error": {"code": exc.code, "message": exc.message}},
        ) from exc

    identity = await get_primary_identity(db, current.organization_id)
    if identity is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "SENDING_IDENTITY_REQUIRED",
                    "message": "Configure and verify a sending identity before approving sends.",
                }
            },
        )
    if identity.sending_paused:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "SENDING_PAUSED",
                    "message": identity.pause_reason
                    or "Sending is paused due to bounce/complaint rates.",
                }
            },
        )
    if not (identity.spf_verified and identity.dkim_verified):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "SENDING_IDENTITY_UNVERIFIED",
                    "message": "SPF and DKIM must both be verified before approving sends.",
                }
            },
        )

    approved = await repo.approve(message, approved_by=current.user_id)
    log_event(
        "message.approved",
        message_id=str(approved.id),
        lead_id=str(approved.lead_id),
        organization_id=str(current.organization_id),
        user_id=str(current.user_id),
    )
    await write_audit(
        db,
        action="message.approve",
        organization_id=current.organization_id,
        user_id=current.user_id,
        resource_type="message",
        resource_id=str(approved.id),
    )
    await db.commit()

    # Enqueue send — worker is the only place that talks to ESP
    try:
        from app.workers.tasks import send_message_task

        send_message_task.delay(str(approved.id))
    except Exception:
        # If Redis/Celery is down, still leave message as approved so it can be
        # retried; surface a soft signal via last_send_error if we can.
        import logging

        logging.getLogger(__name__).exception(
            "Failed to enqueue send for message %s — message stays approved",
            approved.id,
        )

    return approved


@router.post("/{message_id}/reject", response_model=MessageRead)
async def reject_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    repo = MessageRepository(db)
    message = await repo.get_by_id(message_id, current.organization_id)
    if not message:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Message not found"}},
        )
    return await repo.reject(message)


@router.patch("/{message_id}", response_model=MessageRead)
async def update_message(
    message_id: UUID,
    payload: MessageUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Edit message content / subject before approval."""
    repo = MessageRepository(db)
    message = await repo.get_by_id(message_id, current.organization_id)
    if not message:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Message not found"}},
        )
    if message.status not in ("draft", "pending_approval"):
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "NOT_EDITABLE",
                    "message": f"Cannot edit message in status: {message.status}",
                }
            },
        )
    if payload.content is not None:
        message.content = payload.content
    if payload.subject is not None:
        message.subject = payload.subject
    await db.commit()
    await db.refresh(message)
    return message
