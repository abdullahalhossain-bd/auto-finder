"""FastAPI application entrypoint."""
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth, organizations, campaigns, leads, suppression, messages, webhooks, legal, billing, inbox, jobs, usage, followups, invites, admin, demo, referrals, public_growth, lead_quality
from app.api import settings as settings_router
from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging_config import setup_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware

settings = get_settings()
setup_logging(
    level=getattr(settings, "LOG_LEVEL", "INFO"),
    json_logs=(settings.APP_ENV != "development"),
    app_env=settings.APP_ENV,
    service_name="ai-sales-agent",
)

app = FastAPI(
    title="AI Sales Agent API",
    version="0.4.0",
    description="Local Business Opportunity Finder + Safe Outreach Assistant (Stage 1)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(organizations.router, prefix="/api/v1")
app.include_router(campaigns.router, prefix="/api/v1")
app.include_router(leads.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(suppression.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(legal.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
app.include_router(inbox.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(usage.router, prefix="/api/v1")
app.include_router(followups.router, prefix="/api/v1")
app.include_router(invites.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(demo.router, prefix="/api/v1")
app.include_router(referrals.router, prefix="/api/v1")
app.include_router(public_growth.router, prefix="/api/v1")
app.include_router(lead_quality.router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": exc.errors()}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler_wrapper(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return await http_exception_handler(request, exc)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe: process is running."""
    return {"status": "ok", "version": "0.4.0", "stage": "1"}


@app.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Readiness probe: database and Redis must both be reachable."""
    checks: dict[str, str] = {}
    ready = True

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        ready = False

    try:
        import redis.asyncio as redis
        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        try:
            await client.ping()
            checks["redis"] = "ok"
        finally:
            await client.aclose()
    except Exception:
        checks["redis"] = "error"
        ready = False

    payload = {"status": "ready" if ready else "not_ready", "checks": checks}
    return JSONResponse(status_code=200 if ready else 503, content=payload)


@app.get("/health/llm")
async def health_llm() -> dict:
    """Report configured LLM endpoint without performing model inference."""
    try:
        from app.services.llm_service import llm_endpoint_info
        return {"status": "ok", **llm_endpoint_info()}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}
