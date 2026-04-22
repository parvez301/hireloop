"""Unit tests for services/email.py."""

import pytest

from hireloop.services.email import (
    CapturingEmailSender,
    LogEmailSender,
    render_password_reset_email,
    render_verification_code_email,
)


@pytest.mark.asyncio
async def test_log_email_sender_records_sent_messages() -> None:
    sender = LogEmailSender()
    msg = render_verification_code_email(code="123456", email="a@example.com")
    await sender.send(msg)
    assert len(sender.sent) == 1
    assert sender.sent[0].to == "a@example.com"


@pytest.mark.asyncio
async def test_capturing_email_sender_records_sent_messages() -> None:
    sender = CapturingEmailSender()
    msg = render_verification_code_email(code="123456", email="a@example.com")
    await sender.send(msg)
    assert len(sender.sent) == 1


def test_render_verification_code_email_contains_code() -> None:
    msg = render_verification_code_email(code="654321", email="a@example.com")
    assert "654321" in msg.body_text
    assert msg.to == "a@example.com"
    assert "verification" in msg.subject.lower()


def test_render_password_reset_email_contains_token_in_link() -> None:
    msg = render_password_reset_email(
        email="a@example.com",
        token="opaque-reset-token-value",
    )
    assert "opaque-reset-token-value" in msg.body_text
    assert "/auth/reset?token=" in msg.body_text
    assert msg.to == "a@example.com"
