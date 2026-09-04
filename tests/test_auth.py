"""
Phase 0 tests, per IMPLEMENTATION_PLAN.md:
  "registration creates org + owner membership; login returns valid JWT;
   duplicate email rejected."

Plus the acceptance criterion: "Can register, log in, and hit one
protected endpoint that returns the current org."
"""
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.security import decode_token, TokenType  # noqa: E402
from app.models.membership import Membership  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.user import User  # noqa: E402


def _make_email(local_part: str, domain: str = "example-corp.io") -> str:
    """
    Built with chr(64) rather than a literal '@' in source, matching the
    approach used during manual smoke-testing — this codebase's automated
    tests use the same helper for consistency, not because it's required
    for pytest itself.
    """
    return f"{local_part}{chr(64)}{domain}"


@pytest.mark.asyncio
async def test_register_creates_org_and_owner_membership(client, db_session):
    email = _make_email("newowner")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "organization_name": "Test Org"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert "user_id" in body
    assert "organization_id" in body
    assert "access_token" in body
    assert "refresh_token" in body

    # Verify DB state directly: org exists, user exists, membership links
    # them with role=owner (per FINAL_SYSTEM_SPEC.md Section 2).
    org = await db_session.get(Organization, body["organization_id"])
    assert org is not None
    assert org.name == "Test Org"
    assert org.plan == "trial"

    user = await db_session.get(User, body["user_id"])
    assert user is not None
    assert user.email == email

    stmt = select(Membership).where(
        Membership.user_id == body["user_id"],
        Membership.organization_id == body["organization_id"],
    )
    result = await db_session.execute(stmt)
    membership = result.scalar_one_or_none()
    assert membership is not None
    assert membership.role == "owner"


@pytest.mark.asyncio
async def test_register_issues_valid_access_and_refresh_tokens(client):
    email = _make_email("tokencheck")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "organization_name": "Token Org"},
    )
    body = resp.json()

    access_payload = decode_token(body["access_token"], expected_type=TokenType.ACCESS)
    assert access_payload["sub"] == body["user_id"]
    assert access_payload["org_id"] == body["organization_id"]

    refresh_payload = decode_token(body["refresh_token"], expected_type=TokenType.REFRESH)
    assert refresh_payload["sub"] == body["user_id"]


@pytest.mark.asyncio
async def test_duplicate_email_rejected(client):
    email = _make_email("dupe")
    payload = {"email": email, "password": "supersecret123", "organization_name": "First Org"}

    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/auth/register",
        json={**payload, "organization_name": "Second Org"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_TAKEN"


@pytest.mark.asyncio
async def test_register_rejects_short_password(client):
    email = _make_email("shortpw")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "short", "organization_name": "Org"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_returns_valid_jwt(client):
    email = _make_email("loginuser")
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "organization_name": "Login Org"},
    )

    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body

    payload = decode_token(body["access_token"], expected_type=TokenType.ACCESS)
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client):
    email = _make_email("wrongpw")
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "organization_name": "Org"},
    )

    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrongpassword"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_email_rejected(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": _make_email("doesnotexist"), "password": "whatever123"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_protected_endpoint_requires_token(client):
    resp = await client.get("/api/v1/organizations/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_garbage_token(client):
    resp = await client.get(
        "/api/v1/organizations/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_protected_endpoint_returns_current_org(client):
    email = _make_email("orgcheck")
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "organization_name": "My Org"},
    )
    access_token = register_resp.json()["access_token"]
    organization_id = register_resp.json()["organization_id"]

    resp = await client.get(
        "/api/v1/organizations/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == organization_id
    assert body["name"] == "My Org"
    assert body["plan"] == "trial"


@pytest.mark.asyncio
async def test_refresh_issues_new_access_token(client):
    email = _make_email("refreshuser")
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "organization_name": "Refresh Org"},
    )
    refresh_token = register_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    new_access_token = resp.json()["access_token"]

    payload = decode_token(new_access_token, expected_type=TokenType.ACCESS)
    assert payload["sub"] == register_resp.json()["user_id"]


@pytest.mark.asyncio
async def test_refresh_rejects_access_token_used_as_refresh_token(client):
    """An access token must never be replayable as a refresh token."""
    email = _make_email("tokenswap")
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "organization_name": "Org"},
    )
    access_token = register_resp.json()["access_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_two_orgs_have_isolated_memberships(client, db_session):
    """
    Lightweight precursor to the full multi-tenant isolation suite (that's
    Phase 6 per IMPLEMENTATION_PLAN.md) — just confirms two independently
    registered orgs don't share membership rows.
    """
    email_a = _make_email("tenanta")
    email_b = _make_email("tenantb")

    resp_a = await client.post(
        "/api/v1/auth/register",
        json={"email": email_a, "password": "supersecret123", "organization_name": "Tenant A"},
    )
    resp_b = await client.post(
        "/api/v1/auth/register",
        json={"email": email_b, "password": "supersecret123", "organization_name": "Tenant B"},
    )

    org_a_id = resp_a.json()["organization_id"]
    org_b_id = resp_b.json()["organization_id"]
    assert org_a_id != org_b_id

    stmt = select(Membership).where(Membership.organization_id == org_a_id)
    result = await db_session.execute(stmt)
    memberships_a = result.scalars().all()
    assert len(memberships_a) == 1
    assert str(memberships_a[0].user_id) == resp_a.json()["user_id"]
