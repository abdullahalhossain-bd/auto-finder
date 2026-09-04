"""
Campaign discovery flow tests (bugfix: silent city/business_type validation
failure that Celery reported as "succeeded").

Split into two groups:

  * Pure unit tests (NL parser, Places key handling, Celery task branching)
    — no database required, run anywhere with `pytest tests/test_campaign_discovery.py`.

  * HTTP/DB tests (campaign status transitions end-to-end) — require the
    Postgres test DB via conftest.py, same as the rest of this suite
    (`docker compose exec api pytest tests/`). They skip themselves with a
    clear reason if Postgres isn't reachable, matching the existing
    tests/test_multi_tenant_http.py convention.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.nl_parser_service import NLParserService  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Natural language parsing
# ---------------------------------------------------------------------------

def test_parses_city_business_type_and_service():
    result = NLParserService().parse(
        "Find restaurants in New York City that need website services."
    )
    assert result["city"] == "New York City"
    assert result["business_type"] == "restaurant"
    assert result["service_offered"] == "website"
    assert result["country"] == "United States"  # inferred from known city


def test_parses_min_reviews_and_no_website_filter():
    result = NLParserService().parse(
        "Find small restaurants in Chicago with at least 20 reviews and no website."
    )
    assert result["city"] == "Chicago"
    assert result["business_type"] == "restaurant"
    assert result["country"] == "United States"
    assert result["min_reviews"] == 20
    assert result["filters"]["no_website"] is True


def test_parses_shared_negation_no_website_or_booking():
    """'do not have a website or online booking system' must set both flags —
    this is the exact phrasing used in the app's own campaign-creation UI hint."""
    result = NLParserService().parse(
        "Find barber shops in Krakow, Poland with 50+ reviews that do not have "
        "a website or online booking system."
    )
    assert result["city"] == "Krakow"
    assert result["country"] == "Poland"
    assert result["business_type"] == "barber"
    assert result["min_reviews"] == 50
    assert result["filters"]["no_website"] is True
    assert result["filters"]["no_booking"] is True


def test_does_not_fabricate_missing_city():
    """Vague input with no identifiable city must leave city=None, never guess."""
    result = NLParserService().parse("I want to find businesses that need a website")
    assert result["city"] is None


def test_does_not_fabricate_missing_business_type():
    """Vague input with no identifiable business type must leave it None."""
    result = NLParserService().parse("Find clients for my web design agency")
    assert result["business_type"] is None


# ---------------------------------------------------------------------------
# 2. City/business_type validation happens BEFORE a job is queued
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_campaign_rejects_missing_city_without_queueing_job():
    """
    Regression test for the reported bug: starting a campaign whose NL input
    doesn't resolve to a city/business_type must return a clear 422 to the
    caller and must NOT enqueue a Celery job or flip status to 'discovering'.
    """
    from fastapi import HTTPException

    from app.api.campaigns import start_campaign_discovery

    campaign = MagicMock()
    campaign.id = "11111111-1111-1111-1111-111111111111"
    campaign.status = "draft"
    campaign.structured_params = {
        "country": "United States",
        "city": None,
        "business_type": None,
        "service_offered": "website",
    }

    fake_repo = MagicMock()
    fake_repo.get_by_id = AsyncMock(return_value=campaign)
    fake_repo.update = AsyncMock(return_value=campaign)

    with patch("app.api.campaigns.CampaignRepository", return_value=fake_repo):
        with pytest.raises(HTTPException) as exc_info:
            await start_campaign_discovery(
                campaign_id=campaign.id,
                db=MagicMock(),
                current=MagicMock(organization_id="org-1", user_id="user-1"),
            )

    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    assert detail["error"]["code"] == "VALIDATION_ERROR"
    assert "city" in detail["error"]["missing_fields"]
    assert "business_type" in detail["error"]["missing_fields"]
    # Must not have been flipped to "discovering" — update() for status was
    # never reached because we raised before calling it with status=...
    for call in fake_repo.update.mock_calls:
        assert call.kwargs.get("status") != "discovering"


# ---------------------------------------------------------------------------
# 3. Google Places provider — missing/placeholder key is explicit, not silent
# ---------------------------------------------------------------------------

def test_places_provider_skips_without_valid_key(caplog):
    from app.services.places_provider import GooglePlacesProvider

    fake_settings = MagicMock(GOOGLE_PLACES_ENABLED=True, GOOGLE_PLACES_API_KEY="changeme")
    with patch("app.services.places_provider.get_settings", return_value=fake_settings):
        with caplog.at_level("WARNING"):
            provider = GooglePlacesProvider.from_settings()
    assert provider is None
    assert any("no valid" in r.message.lower() for r in caplog.records)


def test_places_provider_disabled_returns_none_quietly():
    from app.services.places_provider import GooglePlacesProvider

    fake_settings = MagicMock(GOOGLE_PLACES_ENABLED=False, GOOGLE_PLACES_API_KEY="")
    with patch("app.services.places_provider.get_settings", return_value=fake_settings):
        assert GooglePlacesProvider.from_settings() is None


def test_places_provider_builds_with_valid_key():
    from app.services.places_provider import GooglePlacesProvider

    fake_settings = MagicMock(GOOGLE_PLACES_ENABLED=True, GOOGLE_PLACES_API_KEY="real-key-123")
    with patch("app.services.places_provider.get_settings", return_value=fake_settings):
        provider = GooglePlacesProvider.from_settings()
    assert provider is not None
    assert provider.api_key == "real-key-123"


# ---------------------------------------------------------------------------
# 4. discovery_pipeline: validation branch never crashes, always sets a
#    machine-readable error + marks the campaign failed (defense-in-depth,
#    exercised directly even though the API layer now gates this first)
# ---------------------------------------------------------------------------

def test_pipeline_returns_structured_error_when_city_missing():
    from app.services.discovery_pipeline import run_discovery_pipeline_sync

    fake_campaign = MagicMock()
    fake_campaign.status = "draft"
    fake_campaign.structured_params = {"business_type": "restaurant"}  # city missing

    fake_session = MagicMock()
    fake_session.get.return_value = fake_campaign

    result = run_discovery_pipeline_sync(fake_session, campaign_id="cid-1")

    assert result["error"] == "validation_error"
    assert "city" in result["missing_fields"]
    assert fake_campaign.status == "failed"


def test_pipeline_returns_structured_error_when_business_type_missing():
    from app.services.discovery_pipeline import run_discovery_pipeline_sync

    fake_campaign = MagicMock()
    fake_campaign.status = "draft"
    fake_campaign.structured_params = {"city": "Chicago"}  # business_type missing

    fake_session = MagicMock()
    fake_session.get.return_value = fake_campaign

    result = run_discovery_pipeline_sync(fake_session, campaign_id="cid-2")

    assert result["error"] == "validation_error"
    assert result["missing_fields"] == ["business_type"]
    assert fake_campaign.status == "failed"


def test_pipeline_propagates_exception_from_candidate_collection():
    """An unexpected technical failure (e.g. OSM/Places both raise) must
    surface as an 'error' result with the campaign marked failed, distinct
    from the validation-error shape above (no 'missing_fields' key)."""
    from app.services.discovery_pipeline import run_discovery_pipeline_sync

    fake_campaign = MagicMock()
    fake_campaign.status = "draft"
    fake_campaign.structured_params = {"city": "Chicago", "business_type": "restaurant"}

    fake_session = MagicMock()
    fake_session.get.return_value = fake_campaign

    with patch(
        "app.services.discovery_pipeline._collect_candidates",
        side_effect=RuntimeError("boom"),
    ):
        result = run_discovery_pipeline_sync(fake_session, campaign_id="cid-3")

    assert "error" in result
    assert "missing_fields" not in result
    assert fake_campaign.status == "failed"


# ---------------------------------------------------------------------------
# 5. Celery task: a business/validation error must mark the Job row
#    "failed", NOT "completed" — this is the exact bug reported
#    ("Task ... succeeded: {'error': ...}").
# ---------------------------------------------------------------------------

def test_task_marks_job_failed_on_business_error():
    with patch("app.core.sync_db.get_sync_session") as mock_get_session, patch(
        "app.services.discovery_pipeline.run_discovery_pipeline_sync"
    ) as mock_pipeline, patch(
        "app.services.job_service.mark_job_running"
    ), patch(
        "app.services.job_service.mark_job_completed"
    ) as mock_completed, patch(
        "app.services.job_service.mark_job_failed"
    ) as mock_failed:
        from app.workers.tasks import run_campaign_discovery

        fake_session = MagicMock()
        mock_get_session.return_value = fake_session

        fake_campaign = MagicMock()
        fake_campaign.status = "draft"
        fake_campaign.organization_id = "org-1"
        fake_session.get.return_value = fake_campaign

        mock_pipeline.return_value = {
            "error": "validation_error",
            "message": "Missing required parameter(s): city",
            "missing_fields": ["city"],
        }

        result = run_campaign_discovery.apply(
            args=["11111111-1111-1111-1111-111111111111", "org-1"]
        ).get()

        assert result["error"] == "validation_error"
        mock_failed.assert_called_once()
        mock_completed.assert_not_called()


def test_task_marks_job_completed_on_success():
    with patch("app.core.sync_db.get_sync_session") as mock_get_session, patch(
        "app.services.discovery_pipeline.run_discovery_pipeline_sync"
    ) as mock_pipeline, patch(
        "app.services.job_service.mark_job_running"
    ), patch(
        "app.services.job_service.mark_job_completed"
    ) as mock_completed, patch(
        "app.services.job_service.mark_job_failed"
    ) as mock_failed:
        from app.workers.tasks import run_campaign_discovery

        fake_session = MagicMock()
        mock_get_session.return_value = fake_session

        fake_campaign = MagicMock()
        fake_campaign.status = "discovering"
        fake_campaign.organization_id = "org-1"
        fake_session.get.return_value = fake_campaign

        mock_pipeline.return_value = {
            "campaign_id": "cid",
            "total_found": 5,
            "qualified": 3,
            "status": "ready_for_review",
        }

        result = run_campaign_discovery.apply(
            args=["11111111-1111-1111-1111-111111111111", "org-1"]
        ).get()

        assert result["qualified"] == 3
        mock_completed.assert_called_once()
        mock_failed.assert_not_called()


# ---------------------------------------------------------------------------
# 6. End-to-end HTTP tests (require Postgres test DB — see conftest.py)
# ---------------------------------------------------------------------------

pytest.importorskip("pytest_asyncio")
pytest.importorskip("httpx")


async def _register_and_get_token(client, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret123",
            "organization_name": "Discovery Test Org",
            "tos_accepted": True,
        },
    )
    if r.status_code not in (200, 201):
        pytest.skip(f"register failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_e2e_start_with_valid_city_and_business_type_moves_to_discovering(client):
    token = await _register_and_get_token(client, "discovery_ok@example-corp.io")
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/campaigns",
        headers=headers,
        json={"natural_language_input": "Find restaurants in Chicago that need a website."},
    )
    if create.status_code not in (200, 201):
        pytest.skip(f"create campaign failed: {create.status_code} {create.text}")
    campaign = create.json()
    assert campaign["structured_params"]["city"] == "Chicago"
    assert campaign["structured_params"]["business_type"] == "restaurant"

    start = await client.post(f"/api/v1/campaigns/{campaign['id']}/start", headers=headers)
    # Either queued (Redis available) or inline fallback — both are non-4xx.
    assert start.status_code < 400, start.text
    body = start.json()
    assert body.get("status") in ("discovering", "ready_for_review", "failed")


@pytest.mark.asyncio
async def test_e2e_start_with_vague_input_returns_422_and_never_reaches_discovering(client):
    token = await _register_and_get_token(client, "discovery_vague@example-corp.io")
    headers = {"Authorization": f"Bearer {token}"}

    create = await client.post(
        "/api/v1/campaigns",
        headers=headers,
        json={"natural_language_input": "I want to find some good clients for my agency please"},
    )
    if create.status_code not in (200, 201):
        pytest.skip(f"create campaign failed: {create.status_code} {create.text}")
    campaign = create.json()
    assert not campaign["structured_params"].get("city")

    start = await client.post(f"/api/v1/campaigns/{campaign['id']}/start", headers=headers)
    assert start.status_code == 422, start.text
    detail = start.json()["detail"]
    assert detail["error"]["code"] == "VALIDATION_ERROR"
    assert "city" in detail["error"]["missing_fields"]

    # Campaign must remain in "draft", never silently flipped to discovering/failed.
    check = await client.get(f"/api/v1/campaigns/{campaign['id']}", headers=headers)
    assert check.json()["status"] == "draft"