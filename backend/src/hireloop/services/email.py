"""Transactional email for the auth flow.

Design goal: the business logic that issues verification codes / reset links
doesn't know or care which transport delivers them. `EMAIL_PROVIDER` env var
picks between:
- `log` (dev default) — writes to structlog.
- `ses` — AWS Simple Email Service via boto3.

Tests inject a CapturingEmailSender via set_email_sender().
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol

from hireloop.config import get_settings
from hireloop.logging import get_logger

log = get_logger("hireloop.email")


@dataclass
class EmailMessage:
    to: str
    subject: str
    body_text: str
    body_html: str | None = None


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


class LogEmailSender:
    """Dev-only sender — logs each send and keeps a list for tests."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        log.info(
            "email_sent",
            to=message.to,
            subject=message.subject,
            body_preview=message.body_text[:200],
        )
        self.sent.append(message)


@dataclass
class CapturingEmailSender:
    """Test seam — explicit capture with zero logging side-effect."""

    sent: list[EmailMessage] = field(default_factory=list)

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class SesEmailSender:
    """AWS SES transport. Requires the sender identity verified in SES and
    the caller's IAM role granted ses:SendEmail on it."""

    def __init__(
        self,
        *,
        from_addr: str,
        from_name: str,
        configuration_set: str | None = None,
    ) -> None:
        self._from = f"{from_name} <{from_addr}>" if from_name else from_addr
        self._configuration_set = configuration_set or None
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client("ses")
        return self._client

    async def send(self, message: EmailMessage) -> None:
        client = self._get_client()
        body: dict[str, Any] = {"Text": {"Data": message.body_text, "Charset": "UTF-8"}}
        if message.body_html:
            body["Html"] = {"Data": message.body_html, "Charset": "UTF-8"}
        kwargs: dict[str, Any] = {
            "Source": self._from,
            "Destination": {"ToAddresses": [message.to]},
            "Message": {
                "Subject": {"Data": message.subject, "Charset": "UTF-8"},
                "Body": body,
            },
        }
        if self._configuration_set:
            kwargs["ConfigurationSetName"] = self._configuration_set
        await asyncio.to_thread(client.send_email, **kwargs)
        log.info(
            "email_sent_ses",
            to=message.to,
            subject=message.subject,
            configuration_set=self._configuration_set,
        )


_sender: EmailSender | None = None


def _build_default_sender() -> EmailSender:
    settings = get_settings()
    provider = settings.email_provider.lower()
    if provider == "ses":
        return SesEmailSender(
            from_addr=settings.email_from,
            from_name=settings.email_from_name,
            configuration_set=settings.email_configuration_set or None,
        )
    return LogEmailSender()


def get_email_sender() -> EmailSender:
    """Factory — returns the transport named by `EMAIL_PROVIDER`."""
    global _sender
    if _sender is None:
        _sender = _build_default_sender()
    return _sender


def set_email_sender(sender: EmailSender | None) -> None:
    """Testing hook — inject a capturing sender, or None to reset."""
    global _sender
    _sender = sender


def render_verification_code_email(*, code: str, email: str) -> EmailMessage:
    subject = "Your HireLoop verification code"
    body_text = (
        f"Hi,\n\nYour HireLoop verification code is:\n\n    {code}\n\n"
        "It expires in 10 minutes. If you didn't request this code, you can\n"
        "safely ignore this email.\n\n— HireLoop\n"
    )
    return EmailMessage(to=email, subject=subject, body_text=body_text)


def render_password_reset_email(*, email: str, token: str) -> EmailMessage:
    settings = get_settings()
    link = f"{settings.app_base_url.rstrip('/')}/auth/reset?token={token}"
    subject = "Reset your HireLoop password"
    body_text = (
        "Hi,\n\nReset your HireLoop password by following this link:\n\n"
        f"    {link}\n\n"
        "The link is valid for 30 minutes and can only be used once. If you\n"
        "didn't request a reset, you can safely ignore this email — your\n"
        "password won't change.\n\n— HireLoop\n"
    )
    return EmailMessage(to=email, subject=subject, body_text=body_text)
