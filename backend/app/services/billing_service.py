"""
Stripe billing (FINAL_SYSTEM_SPEC Section 17).

- Checkout Session for Starter / Pro
- Webhook updates subscriptions + organizations.plan
- Trial orgs get a local subscription row without Stripe until they subscribe

When STRIPE_SECRET_KEY is missing/placeholder, subscribe returns a clear error
so local dev without Stripe still works for trial.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging_config import get_logger, log_event
from app.models.organization import Organization
from app.models.subscription import Subscription
from app.models.user import User

logger = get_logger(__name__)

PLAN_PRICE_ENV = {
    "starter": "STRIPE_PRICE_ID_STARTER",
    "pro": "STRIPE_PRICE_ID_PRO",
}


class BillingError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _stripe_configured() -> bool:
    settings = get_settings()
    key = (settings.STRIPE_SECRET_KEY or "").strip()
    return bool(key) and key not in ("changeme", "sk_test_changeme")


def _get_stripe():
    import stripe

    settings = get_settings()
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


async def ensure_trial_subscription(
    session: AsyncSession, organization_id: UUID
) -> Subscription:
    """Create local trial subscription if missing (register path)."""
    existing = await session.execute(
        select(Subscription).where(Subscription.organization_id == organization_id)
    )
    sub = existing.scalar_one_or_none()
    if sub:
        return sub

    settings = get_settings()
    days = int(getattr(settings, "TRIAL_LENGTH_DAYS", 14) or 14)
    now = datetime.now(timezone.utc)
    sub = Subscription(
        organization_id=organization_id,
        plan_id="trial",
        status="trialing",
        trial_end=now + timedelta(days=days),
        current_period_end=now + timedelta(days=days),
    )
    session.add(sub)
    await session.flush()
    return sub


async def get_subscription(
    session: AsyncSession, organization_id: UUID
) -> Optional[Subscription]:
    result = await session.execute(
        select(Subscription).where(Subscription.organization_id == organization_id)
    )
    return result.scalar_one_or_none()


async def create_checkout_session(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    plan: str,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> dict[str, Any]:
    plan = plan.lower().strip()
    if plan not in ("starter", "pro"):
        raise BillingError("INVALID_PLAN", "plan must be 'starter' or 'pro'")

    from app.demo.adapters import is_demo_mode

    if is_demo_mode():
        raise BillingError(
            "DEMO_MODE",
            "DEMO MODE — no payment gateway is contacted. Ask an admin to "
            "switch this account's plan from the Admin panel instead.",
        )

    if not _stripe_configured():
        raise BillingError(
            "STRIPE_NOT_CONFIGURED",
            "Stripe is not configured on this deployment. Set STRIPE_SECRET_KEY and price IDs.",
        )

    settings = get_settings()
    price_attr = PLAN_PRICE_ENV[plan]
    price_id = (getattr(settings, price_attr, "") or "").strip()
    if not price_id or price_id == "changeme":
        raise BillingError(
            "PRICE_NOT_CONFIGURED",
            f"{price_attr} is not set. Create a Stripe Price and put its id in env.",
        )

    org = await session.get(Organization, organization_id)
    if org is None:
        raise BillingError("ORG_NOT_FOUND", "Organization not found")

    user = await session.get(User, user_id)
    if user is None:
        raise BillingError("USER_NOT_FOUND", "User not found")

    sub = await get_subscription(session, organization_id)
    if sub is None:
        sub = await ensure_trial_subscription(session, organization_id)

    stripe = _get_stripe()
    customer_id = sub.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=org.name,
            metadata={"organization_id": str(organization_id)},
        )
        customer_id = customer["id"]
        sub.stripe_customer_id = customer_id
        await session.flush()

    public = (getattr(settings, "PUBLIC_APP_URL", None) or "http://localhost:5173").rstrip("/")
    # Frontend billing return URLs
    success = success_url or f"{public}/billing?success=1&plan={plan}"
    cancel = cancel_url or f"{public}/billing?cancelled=1"

    checkout = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success if "{CHECKOUT_SESSION_ID}" in success else success + "&session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel,
        client_reference_id=str(organization_id),
        metadata={
            "organization_id": str(organization_id),
            "plan_id": plan,
            "user_id": str(user_id),
        },
        subscription_data={
            "metadata": {
                "organization_id": str(organization_id),
                "plan_id": plan,
            }
        },
    )

    log_event(
        "billing.checkout_created",
        organization_id=str(organization_id),
        plan=plan,
        session_id=checkout.get("id"),
    )
    await session.commit()
    return {
        "checkout_url": checkout["url"],
        "session_id": checkout["id"],
        "plan": plan,
    }


def _ts_to_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


async def apply_subscription_update(
    session: AsyncSession,
    *,
    organization_id: UUID,
    plan_id: str,
    status: str,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    current_period_end: Optional[datetime] = None,
) -> None:
    org = await session.get(Organization, organization_id)
    if org is None:
        logger.warning("billing webhook org missing %s", organization_id)
        return

    sub = await get_subscription(session, organization_id)
    if sub is None:
        sub = Subscription(organization_id=organization_id)
        session.add(sub)

    if stripe_customer_id:
        sub.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        sub.stripe_subscription_id = stripe_subscription_id
    sub.plan_id = plan_id
    sub.status = status
    if current_period_end is not None:
        sub.current_period_end = current_period_end

    # Mirror plan onto organization for simple checks
    if status in ("active", "trialing") and plan_id in ("trial", "starter", "pro"):
        org.plan = plan_id
    if status in ("past_due", "cancelled"):
        # Keep last plan id for display; status blocks creation via plan_limits
        pass

    await session.commit()
    log_event(
        "billing.subscription_updated",
        organization_id=str(organization_id),
        plan_id=plan_id,
        status=status,
    )


async def handle_stripe_event(session: AsyncSession, event: dict[str, Any]) -> dict[str, Any]:
    """Process a verified Stripe event payload."""
    etype = event.get("type") or ""
    data_object = (event.get("data") or {}).get("object") or {}

    log_event("billing.webhook_received", event_type=etype, event_id=event.get("id"))

    if etype == "checkout.session.completed":
        meta = data_object.get("metadata") or {}
        org_id = meta.get("organization_id") or data_object.get("client_reference_id")
        plan_id = (meta.get("plan_id") or "starter").lower()
        if not org_id:
            return {"ok": True, "skipped": "no organization_id"}
        await apply_subscription_update(
            session,
            organization_id=UUID(str(org_id)),
            plan_id=plan_id if plan_id in ("starter", "pro") else "starter",
            status="active",
            stripe_customer_id=data_object.get("customer"),
            stripe_subscription_id=data_object.get("subscription"),
        )
        return {"ok": True, "handled": etype}

    if etype in (
        "customer.subscription.updated",
        "customer.subscription.created",
    ):
        meta = data_object.get("metadata") or {}
        org_id = meta.get("organization_id")
        # Fallback: look up by stripe_subscription_id / customer
        sub = None
        if not org_id:
            sid = data_object.get("id")
            if sid:
                row = await session.execute(
                    select(Subscription).where(Subscription.stripe_subscription_id == sid)
                )
                sub = row.scalar_one_or_none()
                if sub:
                    org_id = str(sub.organization_id)
        if not org_id:
            return {"ok": True, "skipped": "no organization_id"}

        stripe_status = (data_object.get("status") or "").lower()
        status_map = {
            "active": "active",
            "trialing": "trialing",
            "past_due": "past_due",
            "canceled": "cancelled",
            "cancelled": "cancelled",
            "unpaid": "past_due",
            "incomplete": "past_due",
            "incomplete_expired": "cancelled",
        }
        status = status_map.get(stripe_status, "active")
        plan_id = (meta.get("plan_id") or (sub.plan_id if sub else None) or "starter").lower()
        # Infer plan from price id if needed
        items = (data_object.get("items") or {}).get("data") or []
        if items:
            price_id = (items[0].get("price") or {}).get("id")
            settings = get_settings()
            if price_id and price_id == getattr(settings, "STRIPE_PRICE_ID_PRO", None):
                plan_id = "pro"
            elif price_id and price_id == getattr(settings, "STRIPE_PRICE_ID_STARTER", None):
                plan_id = "starter"

        await apply_subscription_update(
            session,
            organization_id=UUID(str(org_id)),
            plan_id=plan_id if plan_id in ("trial", "starter", "pro") else "starter",
            status=status,
            stripe_customer_id=data_object.get("customer"),
            stripe_subscription_id=data_object.get("id"),
            current_period_end=_ts_to_dt(data_object.get("current_period_end")),
        )
        return {"ok": True, "handled": etype}

    if etype == "customer.subscription.deleted":
        meta = data_object.get("metadata") or {}
        org_id = meta.get("organization_id")
        if not org_id:
            sid = data_object.get("id")
            row = await session.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == sid)
            )
            sub = row.scalar_one_or_none()
            if sub:
                org_id = str(sub.organization_id)
        if org_id:
            await apply_subscription_update(
                session,
                organization_id=UUID(str(org_id)),
                plan_id="trial",
                status="cancelled",
                stripe_subscription_id=data_object.get("id"),
            )
        return {"ok": True, "handled": etype}

    if etype == "invoice.payment_failed":
        customer = data_object.get("customer")
        if customer:
            row = await session.execute(
                select(Subscription).where(Subscription.stripe_customer_id == customer)
            )
            sub = row.scalar_one_or_none()
            if sub:
                await apply_subscription_update(
                    session,
                    organization_id=sub.organization_id,
                    plan_id=sub.plan_id,
                    status="past_due",
                    stripe_customer_id=customer,
                    stripe_subscription_id=sub.stripe_subscription_id,
                )
        return {"ok": True, "handled": etype}

    if etype in ("invoice.paid", "invoice.payment_succeeded"):
        # Restore active after successful payment (e.g. recovered from past_due)
        customer = data_object.get("customer")
        sub_id = data_object.get("subscription")
        sub = None
        if sub_id:
            row = await session.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
            )
            sub = row.scalar_one_or_none()
        if sub is None and customer:
            row = await session.execute(
                select(Subscription).where(Subscription.stripe_customer_id == customer)
            )
            sub = row.scalar_one_or_none()
        if sub:
            plan = sub.plan_id if sub.plan_id in ("starter", "pro") else "starter"
            lines = (data_object.get("lines") or {}).get("data") or []
            settings = get_settings()
            for line in lines:
                price_id = ((line.get("price") or {}).get("id")) or ""
                if price_id and price_id == getattr(settings, "STRIPE_PRICE_ID_PRO", None):
                    plan = "pro"
                elif price_id and price_id == getattr(settings, "STRIPE_PRICE_ID_STARTER", None):
                    plan = "starter"
            await apply_subscription_update(
                session,
                organization_id=sub.organization_id,
                plan_id=plan,
                status="active",
                stripe_customer_id=customer or sub.stripe_customer_id,
                stripe_subscription_id=sub_id or sub.stripe_subscription_id,
                current_period_end=_ts_to_dt(data_object.get("period_end")),
            )
        return {"ok": True, "handled": etype}

    return {"ok": True, "ignored": etype}



async def create_billing_portal_session(
    session: AsyncSession,
    *,
    organization_id: UUID,
    return_url: Optional[str] = None,
) -> dict[str, Any]:
    """Stripe Customer Portal for plan changes / payment method / cancel."""
    from app.demo.adapters import is_demo_mode

    if is_demo_mode():
        raise BillingError(
            "DEMO_MODE",
            "DEMO MODE — the Stripe customer portal is disabled. Use the "
            "Admin panel to change plans in this demo.",
        )

    if not _stripe_configured():
        raise BillingError(
            "STRIPE_NOT_CONFIGURED",
            "Stripe is not configured on this deployment.",
        )
    sub = await get_subscription(session, organization_id)
    if sub is None or not sub.stripe_customer_id:
        raise BillingError(
            "NO_CUSTOMER",
            "No Stripe customer yet. Subscribe to a plan first.",
        )
    settings = get_settings()
    public = (getattr(settings, "PUBLIC_APP_URL", None) or "http://localhost:5173").rstrip("/")
    ret = return_url or f"{public}/billing"
    stripe = _get_stripe()
    try:
        portal = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=ret,
        )
    except Exception as exc:
        logger.exception("billing portal session failed")
        raise BillingError("PORTAL_FAILED", str(exc)[:300]) from exc
    return {"portal_url": portal["url"]}


def construct_webhook_event(payload: bytes, sig_header: str) -> dict[str, Any]:
    if not _stripe_configured():
        raise BillingError("STRIPE_NOT_CONFIGURED", "Stripe is not configured")
    settings = get_settings()
    secret = (settings.STRIPE_WEBHOOK_SECRET or "").strip()
    if not secret or secret == "changeme":
        raise BillingError("WEBHOOK_SECRET_MISSING", "STRIPE_WEBHOOK_SECRET is not set")
    stripe = _get_stripe()
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except Exception as exc:
        raise BillingError("INVALID_SIGNATURE", f"Webhook signature verification failed: {exc}") from exc
    return event if isinstance(event, dict) else dict(event)
