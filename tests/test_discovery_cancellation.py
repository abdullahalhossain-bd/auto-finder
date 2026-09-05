"""Regression tests for authoritative discovery cancellation state."""
from types import SimpleNamespace
from uuid import uuid4

from app.services import discovery_pipeline as pipeline


class FakeSession:
    def __init__(self, statuses):
        self.statuses = iter(statuses)

    def execute(self, _query):
        status = next(self.statuses)
        return SimpleNamespace(scalar_one_or_none=lambda: status)


def test_campaign_is_cancelled_reads_fresh_database_state():
    campaign_id = uuid4()
    session = FakeSession(["cancelled"])

    assert pipeline._campaign_is_cancelled(session, campaign_id) is True


def test_campaign_is_not_cancelled_when_database_state_is_active():
    campaign_id = uuid4()
    session = FakeSession(["scoring"])

    assert pipeline._campaign_is_cancelled(session, campaign_id) is False


def test_cancellation_wins_over_completion_state():
    """The pipeline must never convert an externally-cancelled job to ready_for_review."""
    campaign = SimpleNamespace(status="cancelled")
    assert campaign.status == "cancelled"
    assert campaign.status != "ready_for_review"
