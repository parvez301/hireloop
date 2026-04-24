"""Public LLM routing entry point.

Single function: `resolve(task)` returns the (Provider, model) pair to use.
Call sites stay thin — they ask the router which provider+model to use, then
hand off to the provider client (`anthropic_client`, `gemini_client`,
`groq_client`).

Phase 1 deliberately does NOT refactor existing call sites. This module is
infrastructure; the cutover happens in Phase 7 once the personalisation stack
(Phases 2–6) is in place.
"""

from __future__ import annotations

from dataclasses import dataclass

from hireloop.core.llm.tier import Provider, Task, Tier, model_for, provider_for, tier_for


@dataclass(frozen=True)
class Route:
    task: Task
    tier: Tier
    provider: Provider
    model: str


def resolve(task: Task) -> Route:
    tier = tier_for(task)
    provider = provider_for(tier)
    return Route(task=task, tier=tier, provider=provider, model=model_for(provider))
