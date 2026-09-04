from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, CurrentUser
from app.repositories.suppression_repository import SuppressionRepository
from app.schemas.suppression import SuppressionCreate, SuppressionRead

router = APIRouter(prefix="/suppression", tags=["suppression"])


@router.post("", response_model=SuppressionRead, status_code=status.HTTP_201_CREATED)
async def add_to_suppression(
    payload: SuppressionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    repo = SuppressionRepository(db)
    entry = await repo.add(current.organization_id, payload.contact_value, payload.reason)
    return entry


@router.get("", response_model=list[SuppressionRead])
async def list_suppression(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    repo = SuppressionRepository(db)
    items, _ = await repo.list_by_org(current.organization_id, limit=limit, offset=offset)
    return items
