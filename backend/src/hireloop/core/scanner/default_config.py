"""Default 15-company scan config seeded at onboarding.

Parent spec Appendix M. Seeded eagerly when a user's profile transitions to
onboarding_state='done', but NOT auto-run — the user must explicitly click
'Run scan' or ask the agent to scan.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.scan_config import ScanConfig

DEFAULT_SCAN_CONFIG_NAME = "AI & Developer Tools Companies"

DEFAULT_COMPANIES: list[dict[str, Any]] = [
    # Greenhouse
    {"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"},
    {"name": "Airtable", "platform": "greenhouse", "board_slug": "airtable"},
    {"name": "Figma", "platform": "greenhouse", "board_slug": "figma"},
    {"name": "Vercel", "platform": "greenhouse", "board_slug": "vercel"},
    {"name": "Notion", "platform": "greenhouse", "board_slug": "notion"},
    # Ashby
    {"name": "Linear", "platform": "ashby", "board_slug": "linear"},
    {"name": "Anthropic", "platform": "ashby", "board_slug": "anthropic"},
    {"name": "Ramp", "platform": "ashby", "board_slug": "ramp"},
    {"name": "OpenAI", "platform": "ashby", "board_slug": "openai"},
    {"name": "Perplexity", "platform": "ashby", "board_slug": "perplexity"},
    # Lever
    {"name": "Netflix", "platform": "lever", "board_slug": "netflix"},
    {"name": "Shopify", "platform": "lever", "board_slug": "shopify"},
    {"name": "GitLab", "platform": "lever", "board_slug": "gitlab"},
    {"name": "Postman", "platform": "lever", "board_slug": "postman"},
    {"name": "Asana", "platform": "lever", "board_slug": "asana"},
]


async def seed_default_scan_config(session: AsyncSession, user_id: UUID) -> ScanConfig:
    """Create the default config for a user. Idempotent.

    Does NOT trigger a scan run. The user must explicitly click 'Run scan' or
    ask the agent. This avoids hidden first-session cost at signup.
    """
    stmt = select(ScanConfig).where(
        ScanConfig.user_id == user_id,
        ScanConfig.name == DEFAULT_SCAN_CONFIG_NAME,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing

    config = ScanConfig(
        user_id=user_id,
        name=DEFAULT_SCAN_CONFIG_NAME,
        companies=list(DEFAULT_COMPANIES),
        keywords=None,
        exclude_keywords=None,
        schedule="manual",
        is_active=True,
    )
    session.add(config)
    await session.flush()
    return config
