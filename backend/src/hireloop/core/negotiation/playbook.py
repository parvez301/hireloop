"""NegotiationPlaybook — Claude call using parent spec Appendix D.7 prompt.

Market context is pulled from Claude's training data. No live market API in 2d.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from hireloop.config import get_settings
from hireloop.core.llm.anthropic_client import CallRoute, complete_with_cache
from hireloop.core.llm.errors import LLMParseError
from hireloop.core.llm.personalisation import with_personalisation

_CACHEABLE_INSTRUCTIONS = """You are a salary negotiation coach. Generate a complete negotiation
playbook for an offer based on the candidate's situation and the market.

OUTPUT STRUCTURE:
- market_research: low/mid/high range + source notes + comparable roles
- counter_offer: target, minimum acceptable, equity ask, justification
- scripts: email template, call script, fallback positions, pitfalls
- Pull market data from levels.fyi, glassdoor, blind, and comparable role postings
  you know about. Cite sources in source_notes.
- Counter target should be 10-20% above the offer's base by default, adjusted for
  the candidate's experience and market signal.
- Scripts must use the offer details verbatim — don't substitute placeholder numbers.

OUTPUT JSON SCHEMA:
{
  "market_research": {
    "range_low": 180000,
    "range_mid": 205000,
    "range_high": 240000,
    "source_notes": "Based on levels.fyi and Glassdoor for {role} at {seniority} in {location}",
    "comparable_roles": ["Company A ~200k", "Company B ~215k"]
  },
  "counter_offer": {
    "target": 220000,
    "minimum_acceptable": 200000,
    "equity_ask": "0.15% or $30k additional RSU",
    "justification": "Based on market data and experience with distributed systems..."
  },
  "scripts": {
    "email_template": "Hi {recruiter},\\n\\nThanks so much for the offer...",
    "call_script": "Opening: '...'\\nCounter: '...'\\nIf pushback: '...'\\nClose: '...'",
    "fallback_positions": [
      "If salary is firm, ask for signing bonus of $X",
      "If total comp is firm, ask for earlier review cycle"
    ],
    "pitfalls": [
      "Don't accept the first counter without asking for 48 hours",
      "Don't negotiate over text — voice or video only"
    ]
  }
}

No prose outside JSON."""

_SYSTEM = with_personalisation(
    "You are a salary negotiation coach. Output only strict JSON matching the schema."
)


@dataclass
class GeneratedPlaybook:
    market_research: dict[str, Any]
    counter_offer: dict[str, Any]
    scripts: dict[str, Any]
    usage: Any
    model: str


async def generate_negotiation_playbook(
    *,
    title: str,
    company: str,
    location: str | None,
    offer_details: dict[str, Any],
    current_comp: dict[str, Any] | None,
    experience_summary: str,
    feedback: str | None = None,
    route: CallRoute = "realtime",
) -> GeneratedPlaybook:
    """One-shot Claude call. Uses prompt caching on the instructions block."""
    settings = get_settings()
    feedback_block = f"\n\nUSER FEEDBACK FROM PRIOR ATTEMPT:\n{feedback}" if feedback else ""
    user_block = (
        f"INPUT:\n"
        f"Role: {title} at {company}\n"
        f"Location: {location or 'not specified'}\n"
        f"Offer Details: {json.dumps(offer_details)}\n"
        f"Current Comp: {json.dumps(current_comp) if current_comp else 'not provided'}\n"
        f"Candidate Experience: {experience_summary}"
        f"{feedback_block}\n\n"
        "Generate a complete negotiation playbook. Output JSON only."
    )

    result = await complete_with_cache(
        system=_SYSTEM,
        cacheable_blocks=[_CACHEABLE_INSTRUCTIONS],
        user_block=user_block,
        model=settings.claude_model,
        max_tokens=3000,
        timeout_s=settings.llm_evaluation_timeout_s,
        route=route,
    )
    parsed = _parse(result.text)
    return GeneratedPlaybook(
        market_research=parsed["market_research"],
        counter_offer=parsed["counter_offer"],
        scripts=parsed["scripts"],
        usage=result.usage,
        model=result.model,
    )


def _parse(text: str) -> dict[str, Any]:
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMParseError(
            "Negotiation playbook returned invalid JSON",
            provider="anthropic",
            details={"raw": raw[:500]},
        ) from e
    for required in ("market_research", "counter_offer", "scripts"):
        if required not in data:
            raise LLMParseError(
                f"Missing '{required}' field in playbook response",
                provider="anthropic",
            )
    return data
