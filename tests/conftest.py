"""
Shared pytest fixtures.

Uses DATABASE_URL_TEST (per ENVIRONMENT_CONFIG.md's environment-separation
table: "separate _test DB, wiped between runs").

Design note: asyncpg connections are bound to the event loop they were
created on. pytest-asyncio 0.25 gives each async test function its own
event loop by default, so a single async engine created once at import
time (or session scope) breaks the second test with
"attached to a different loop" / "another operation is in progress".
The fix used here: schema setup/teardown uses a plain *synchronous*
engine (psycopg2, no event loop involved at all), while each test gets
its own fresh async engine created inside that test's own event loop.
"""
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Import all models so Base.metadata is fully populated before create_all.
from app import models  # noqa: E402, F401

_settings = get_settings()


def _sync_test_url() -> str:
    """DATABASE_URL_TEST as a plain psycopg2 URL (async driver swapped out)."""
    return _settings.DATABASE_URL_TEST.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    """Create all tables once for the whole test session (sync engine, no event loop involved)."""
    sync_engine = create_engine(_sync_test_url())
    with sync_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        Base.metadata.create_all(conn)
    yield
    with sync_engine.begin() as conn:
        Base.metadata.drop_all(conn)
    sync_engine.dispose()


@pytest.fixture(autouse=True)
def _truncate_tables():
    """Truncates all app tables after every test (sync engine) so tests don't leak state."""
    yield
    sync_engine = create_engine(_sync_test_url())
    with sync_engine.begin() as conn:
        table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        if table_names:
            conn.execute(text(f"TRUNCATE {table_names} CASCADE"))
    sync_engine.dispose()


@pytest_asyncio.fixture
async def async_session_factory():
    """
    A fresh async engine + sessionmaker created inside THIS test's own
    event loop, so asyncpg's loop-binding is always satisfied.
    """
    engine = create_async_engine(_settings.DATABASE_URL_TEST)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def client(async_session_factory):
    """httpx AsyncClient wired to the FastAPI app, get_db overridden to use the test engine."""

    async def _override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_session(async_session_factory):
    """A standalone session for tests to assert DB state directly."""
    async with async_session_factory() as session:
        yield session
