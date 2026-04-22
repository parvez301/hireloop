"""Transactional email for the auth flow.

Design goal: the business logic that issues verification codes / reset links
doesn't know or care which transport delivers them. Swap providers (SES,
Postmark, Resend) by changing only the factory below.

For dev we ship a `LogEmailSender` that prints the email body to logs and
stashes the payload on the instance for test-time assertions. Tests can
inject a capturing sender without patching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

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


_sender: EmailSender | None = None


def get_email_sender() -> EmailSender:
    """Factory — swap the class here when a real transport is wired."""
    global _sender
    if _sender is None:
        _sender = LogEmailSender()
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
