"""Write audit_logs rows for sensitive actions."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    action: str,
    organization_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
    detail: Optional[str] = None,
) -> AuditLog:
    row = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip=ip,
        user_agent=user_agent,
        meta=meta,
        detail=detail,
    )
    session.add(row)
    await session.flush()
    return row


def write_audit_sync(
    session: Session,
    *,
    action: str,
    organization_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
    detail: Optional[str] = None,
) -> AuditLog:
    row = AuditLog(
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        meta=meta,
        detail=detail,
    )
    session.add(row)
    session.flush()
    return row
