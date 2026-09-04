"""
Synchronous SQLAlchemy session for Celery workers.

Workers are sync processes; the FastAPI path stays async via database.py.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import get_settings


def _sync_url(async_url: str) -> str:
    # postgresql+asyncpg:// → postgresql+psycopg2:// or postgresql://
    if "+asyncpg" in async_url:
        return async_url.replace("+asyncpg", "")
    if async_url.startswith("postgresql+asyncpg"):
        return async_url.replace("postgresql+asyncpg", "postgresql")
    return async_url


_settings = get_settings()
_engine = create_engine(_sync_url(_settings.DATABASE_URL), pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_sync_session() -> Session:
    return SyncSessionLocal()
