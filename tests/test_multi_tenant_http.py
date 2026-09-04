"""
Cross-org isolation HTTP tests.

Requires Postgres test DB + conftest (skipped automatically if unavailable).
"""
import pytest

pytest.importorskip("pytest_asyncio")
pytest.importorskip("httpx")


@pytest.mark.asyncio
async def test_org_a_cannot_read_org_b_campaign(client, db_session):
    """Register two orgs; A must not see B's campaign (404)."""
    # Register org A
    r1 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner_a@example-corp.io",
            "password": "supersecret123",
            "organization_name": "Org A",
            "tos_accepted": True,
        },
    )
    if r1.status_code not in (200, 201):
        pytest.skip(f"register failed: {r1.status_code} {r1.text}")
    token_a = r1.json().get("access_token")

    r2 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner_b@example-corp.io",
            "password": "supersecret123",
            "organization_name": "Org B",
            "tos_accepted": True,
        },
    )
    if r2.status_code not in (200, 201):
        pytest.skip(f"register B failed: {r2.status_code}")
    token_b = r2.json().get("access_token")

    # B creates campaign
    cb = await client.post(
        "/api/v1/campaigns",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"natural_language_input": "Find bakeries in Krakow"},
    )
    if cb.status_code not in (200, 201):
        pytest.skip(f"create campaign failed: {cb.status_code} {cb.text}")
    camp_id = cb.json()["id"]

    # A tries to read B's campaign
    ra = await client.get(
        f"/api/v1/campaigns/{camp_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert ra.status_code == 404, ra.text
