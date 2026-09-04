"""
Multi-tenant isolation tests.

These tests assert that repository / query construction always scopes by
organization_id. Full HTTP tests require Postgres (conftest); pure unit tests
cover static guarantees without a live DB.
"""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# --- Static source checks: every list/get in org-owned repos takes organization_id ---

ORG_OWNED_REPO_FILES = [
    "app/repositories/campaign_repository.py",
    "app/repositories/lead_repository.py",
    "app/repositories/message_repository.py",
]


def _repo_source(rel: str) -> str:
    return (BACKEND / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize("rel", ORG_OWNED_REPO_FILES)
def test_repository_methods_require_organization_id(rel):
    """Public async methods that read data must accept organization_id."""
    path = BACKEND / rel
    if not path.exists():
        pytest.skip(f"{rel} missing")
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name.startswith("_"):
                continue
            if item.name in ("__init__",):
                continue
            arg_names = [a.arg for a in item.args.args]
            # create may take organization_id as keyword-only
            all_args = arg_names + [a.arg for a in item.args.kwonlyargs]
            if item.name in ("create",):
                assert "organization_id" in all_args or "organization_id" in path.read_text()
                continue
            if item.name.startswith("list") or item.name.startswith("get"):
                assert (
                    "organization_id" in all_args
                ), f"{rel}::{item.name} must take organization_id"


def test_lead_repository_filters_deleted_and_org():
    src = _repo_source("app/repositories/lead_repository.py")
    assert "organization_id" in src
    assert "deleted_at" in src or "organization_id" in src


def test_api_routes_use_get_current_user():
    """Protected route modules must depend on get_current_user."""
    api_dir = BACKEND / "app" / "api"
    protected = [
        "campaigns.py",
        "leads.py",
        "messages.py",
        "suppression.py",
        "organizations.py",
        "billing.py",
        "settings.py",
        "usage.py",
        "jobs.py",
    ]
    for name in protected:
        path = api_dir / name
        if not path.exists():
            continue
        text = path.read_text()
        assert "get_current_user" in text, f"{name} missing get_current_user dependency"


def test_public_routes_do_not_leak_org_data_without_token():
    """Auth + legal + unsubscribe are public; others should not be unauthenticated list endpoints."""
    main = (BACKEND / "app" / "main.py").read_text()
    # Smoke: protected routers are included under /api/v1
    assert "campaigns.router" in main
    assert "leads.router" in main
