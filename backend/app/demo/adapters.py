"""
Mock adapters for DEMO_MODE.

UI → Service Layer → Mock Adapters → Demo fixtures
(Later: swap Mock* for Real* without changing UI contracts.)
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.demo.fixtures import (
    demo_customer_reply,
    demo_message_for_lead,
    filter_demo_businesses,
)

logger = logging.getLogger(__name__)


def is_demo_mode() -> bool:
    return bool(getattr(get_settings(), "DEMO_MODE", False))


class MockDiscoveryAdapter:
    """Simulates Maps / Search / Facebook collection — local fixtures only."""

    SOURCE_STEPS = [
        ("initializing", "Initializing demo discovery"),
        ("google_maps", "Simulating Google Maps search"),
        ("google_search", "Simulating Google Search enrichment"),
        ("facebook", "Simulating Facebook page signals"),
        ("collecting", "Collecting businesses from demo catalog"),
        ("deduping", "Removing duplicates"),
        ("scoring", "Scoring opportunities (rules)"),
        ("completed", "Demo generation completed"),
    ]

    def search(
        self,
        *,
        industry: str | None = None,
        city: str | None = None,
        limit: int = 40,
    ) -> dict[str, Any]:
        if not is_demo_mode():
            raise RuntimeError("MockDiscoveryAdapter only runs when DEMO_MODE=true")

        logger.info(
            "demo.discovery mock industry=%s city=%s limit=%s (no external APIs)",
            industry,
            city,
            limit,
        )
        businesses = filter_demo_businesses(industry=industry, city=city, limit=limit)
        # Fake dupe removed count
        dupes = 2 if len(businesses) > 5 else 0
        qualified = [b for b in businesses if b["opportunity_score"] >= 45]
        hot = [b for b in businesses if b["opportunity_score"] >= 80]
        by_source: dict[str, int] = {}
        for b in businesses:
            s = b.get("source") or "demo"
            by_source[s] = by_source.get(s, 0) + 1

        return {
            "demo_mode": True,
            "label": "DEMO DATA — sources are simulated labels only",
            "businesses": businesses,
            "stats": {
                "total_generated": len(businesses),
                "qualified": len(qualified),
                "hot": len(hot),
                "duplicates_removed": dupes,
                "by_source": by_source,
            },
            "steps": [{"id": s[0], "label": s[1]} for s in self.SOURCE_STEPS],
        }


class MockLLMAdapter:
    """Deterministic message drafts — no remote AI."""

    def personalize(self, business: dict[str, Any], service: str = "websites and online booking") -> dict[str, Any]:
        if not is_demo_mode():
            raise RuntimeError("MockLLMAdapter only in DEMO_MODE")
        msg = demo_message_for_lead(business, service)
        return {
            **msg,
            "provider": "demo_template",
            "used_fallback": False,
            "demo_mode": True,
        }

    def analyze_reply(self, text: str | None = None, intent: str = "positive") -> dict[str, Any]:
        return {**demo_customer_reply(intent), "demo_mode": True}


class MockESPAdapter:
    def send(self, *, to_email: str, subject: str, body: str) -> dict[str, Any]:
        logger.info("demo.esp simulated send to=%s subject=%s", to_email, subject[:40])
        return {
            "ok": True,
            "provider": "demo_console",
            "message_id": f"demo-{uuid4()}",
            "demo_mode": True,
            "note": "No email provider contacted",
        }


class MockBillingAdapter:
    def checkout_url(self, plan: str) -> dict[str, Any]:
        return {
            "demo_mode": True,
            "url": None,
            "message": "DEMO MODE — payments disabled. Use Admin to switch plans.",
            "plan": plan,
        }

    def portal_url(self) -> dict[str, Any]:
        return {
            "demo_mode": True,
            "url": None,
            "message": "DEMO MODE — Stripe portal not available.",
        }


# In-memory generation job progress for buyer demo UX
_GEN_JOBS: dict[str, dict[str, Any]] = {}


def start_demo_generation_job(
    *,
    industry: str,
    city: str,
    limit: int = 40,
) -> str:
    job_id = str(uuid4())
    _GEN_JOBS[job_id] = {
        "id": job_id,
        "status": "running",
        "step_index": 0,
        "industry": industry,
        "city": city,
        "limit": limit,
        "created": time.time(),
        "result": None,
    }
    return job_id


def tick_demo_generation_job(job_id: str) -> dict[str, Any]:
    job = _GEN_JOBS.get(job_id)
    if not job:
        return {"error": "job_not_found"}
    steps = MockDiscoveryAdapter.SOURCE_STEPS
    if job["status"] == "completed":
        return job
    job["step_index"] = min(job["step_index"] + 1, len(steps) - 1)
    step_id, step_label = steps[job["step_index"]]
    job["current_step"] = step_id
    job["current_label"] = step_label
    if step_id == "completed":
        result = MockDiscoveryAdapter().search(
            industry=job["industry"], city=job["city"], limit=job["limit"]
        )
        job["result"] = result
        job["status"] = "completed"
    return job
