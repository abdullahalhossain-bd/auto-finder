"""
ESP (Email Service Provider) client.

Providers:
  - console  (default, FREE) — logs the email; marks as sent. No API key, no cost.
  - resend   — optional free-tier Resend API when ESP_API_KEY is set.
  - smtp     — optional plain SMTP (e.g. local Mailhog / free provider).

No paid LLM or paid-only ESP is required. Resend free tier is opt-in via key.
"""
from __future__ import annotations

import logging
import re
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

UNSUBSCRIBE_MARKER = "unsubscribe"
# Simple pattern: any http(s) link containing "unsubscribe"
_UNSUB_LINK_RE = re.compile(
    r"https?://[^\s<>\"]*unsubscribe[^\s<>\"]*",
    re.IGNORECASE,
)


@dataclass
class SendResult:
    success: bool
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    provider: str = "console"


class EspClient(ABC):
    @abstractmethod
    def send(
        self,
        *,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        text_body: str,
        reply_to: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> SendResult:
        ...


class ConsoleEspClient(EspClient):
    """Zero-cost provider: writes the outbound email to logs only."""

    def send(
        self,
        *,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        text_body: str,
        reply_to: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> SendResult:
        logger.info(
            "ESP[console] SEND to=%s from=%s <%s> subject=%r body_preview=%r",
            to_email,
            from_name,
            from_email,
            subject,
            (text_body or "")[:200],
        )
        # Synthetic id so we can still track "delivery" in DB
        import uuid

        return SendResult(
            success=True,
            provider_message_id=f"console-{uuid.uuid4()}",
            provider="console",
        )


class ResendEspClient(EspClient):
    """Resend.com HTTP API (free tier available). Only used when ESP_API_KEY is set."""

    API_URL = "https://api.resend.com/emails"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def send(
        self,
        *,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        text_body: str,
        reply_to: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> SendResult:
        payload: dict = {
            "from": f"{from_name} <{from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        }
        if reply_to:
            payload["reply_to"] = reply_to
        if headers:
            payload["headers"] = headers

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    self.API_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
            if resp.status_code in (200, 201):
                data = resp.json()
                return SendResult(
                    success=True,
                    provider_message_id=data.get("id"),
                    provider="resend",
                )
            return SendResult(
                success=False,
                error=f"Resend HTTP {resp.status_code}: {resp.text[:500]}",
                provider="resend",
            )
        except Exception as exc:  # noqa: BLE001 — surface to send worker
            logger.exception("Resend send failed")
            return SendResult(success=False, error=str(exc), provider="resend")


class SmtpEspClient(EspClient):
    """Plain SMTP — free with Mailhog (local) or any SMTP relay you already have."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send(
        self,
        *,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        text_body: str,
        reply_to: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> SendResult:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        if reply_to:
            msg["Reply-To"] = reply_to
        if headers:
            for k, v in headers.items():
                msg[k] = v
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                if self.use_tls:
                    server.starttls()
                if self.username:
                    server.login(self.username, self.password)
                server.sendmail(from_email, [to_email], msg.as_string())
            import uuid

            return SendResult(
                success=True,
                provider_message_id=f"smtp-{uuid.uuid4()}",
                provider="smtp",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("SMTP send failed")
            return SendResult(success=False, error=str(exc), provider="smtp")


def get_esp_client() -> EspClient:
    """
    Factory. Default is console (no cost).
    Set ESP_PROVIDER=resend + ESP_API_KEY for Resend free tier,
    or ESP_PROVIDER=smtp + SMTP_* for local Mailhog / free SMTP.
    """
    settings = get_settings()
    provider = getattr(settings, "ESP_PROVIDER", "console") or "console"
    # Treat missing/placeholder key as console so we never call paid APIs by accident
    api_key = (getattr(settings, "ESP_API_KEY", "") or "").strip()
    if provider == "resend" and api_key and api_key != "changeme":
        return ResendEspClient(api_key=api_key)
    if provider == "smtp":
        return SmtpEspClient(
            host=getattr(settings, "SMTP_HOST", "localhost"),
            port=int(getattr(settings, "SMTP_PORT", 1025)),
            username=getattr(settings, "SMTP_USERNAME", "") or "",
            password=getattr(settings, "SMTP_PASSWORD", "") or "",
            use_tls=bool(getattr(settings, "SMTP_USE_TLS", False)),
        )
    # Default: free console logger
    if provider == "resend" and (not api_key or api_key == "changeme"):
        logger.warning(
            "ESP_PROVIDER=resend but ESP_API_KEY is missing/placeholder — using console (free)"
        )
    return ConsoleEspClient()


def ensure_unsubscribe_link(content: str, unsubscribe_url: str) -> str:
    """
    Server-side mandatory unsubscribe injection.
    If content already has an unsubscribe URL, leave it; otherwise append one.
    """
    if _UNSUB_LINK_RE.search(content):
        return content
    footer = (
        f"\n\n---\n"
        f"To unsubscribe from future messages, visit: {unsubscribe_url}\n"
        f"If you did not expect this email, you can ignore it or use the link above.\n"
    )
    return content.rstrip() + footer


def content_has_unsubscribe_link(content: str) -> bool:
    return bool(_UNSUB_LINK_RE.search(content))
