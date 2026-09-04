"""Public legal documents — no auth required."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/legal", tags=["legal"])

_DOCS = Path(__file__).resolve().parents[3] / "docs" / "legal"


def _read(name: str) -> str:
    path = _DOCS / name
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return f"# {name}\n\nDocument not found on this deployment."


@router.get("/privacy", response_class=PlainTextResponse)
async def privacy_policy() -> str:
    return _read("PRIVACY_POLICY.md")


@router.get("/terms", response_class=PlainTextResponse)
async def terms_of_service() -> str:
    return _read("TERMS_OF_SERVICE.md")
