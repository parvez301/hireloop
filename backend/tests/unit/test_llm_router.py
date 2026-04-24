"""Tests for the LLM tier taxonomy and router.

Locks in the routing matrix from MODEL_ROUTING_STRATEGY.md so accidental
mis-routing of expensive Sonnet calls onto Groq (or vice versa) is caught.
"""

from __future__ import annotations

import pytest

from hireloop.config import get_settings
from hireloop.core.llm.router import resolve
from hireloop.core.llm.tier import (
    Provider,
    Task,
    Tier,
    model_for,
    provider_for,
    tier_for,
)

_FAST_TASKS = {
    Task.INTENT_CLASSIFY,
    Task.JOB_CLASSIFY,
    Task.JOB_DEDUP,
    Task.SALARY_EXTRACT,
    Task.JD_ENTITY_EXTRACT,
    Task.SESSION_TRIGGER,
    Task.YES_NO_PRESCREEN,
}

_BALANCED_TASKS = {
    Task.CV_STRUCTURE_EXTRACT,
    Task.PROFILE_EXTRACT,
    Task.QUICK_FIT_SCORE,
    Task.GAP_SUMMARY,
    Task.INTERVIEW_QUESTIONS,
    Task.LINKEDIN_MESSAGE,
    Task.APPLICATION_FORM_ANSWERS,
    Task.PDF_STRUCTURE,
    Task.JOB_TITLE_NORMALISE,
    Task.CROSSREF_MAP,
}

_QUALITY_TASKS = {
    Task.FULL_EVALUATION,
    Task.STAR_STORY,
    Task.CV_REWRITE,
    Task.COVER_LETTER,
    Task.NEGOTIATION_SCRIPT,
    Task.SMART_APPLY_CV,
    Task.SMART_APPLY_COVER,
}


def test_every_task_is_classified_into_a_tier() -> None:
    classified = _FAST_TASKS | _BALANCED_TASKS | _QUALITY_TASKS
    assert classified == set(Task), (
        "Every Task must be assigned a tier in tier.py — unclassified: " f"{set(Task) - classified}"
    )


@pytest.mark.parametrize("task", sorted(_FAST_TASKS, key=lambda t: t.value))
def test_fast_tasks_route_to_groq(task: Task) -> None:
    assert tier_for(task) is Tier.FAST
    assert provider_for(Tier.FAST) is Provider.GROQ


@pytest.mark.parametrize("task", sorted(_BALANCED_TASKS, key=lambda t: t.value))
def test_balanced_tasks_route_to_gemini(task: Task) -> None:
    assert tier_for(task) is Tier.BALANCED
    assert provider_for(Tier.BALANCED) is Provider.GEMINI


@pytest.mark.parametrize("task", sorted(_QUALITY_TASKS, key=lambda t: t.value))
def test_quality_tasks_route_to_anthropic(task: Task) -> None:
    assert tier_for(task) is Tier.QUALITY
    assert provider_for(Tier.QUALITY) is Provider.ANTHROPIC


def test_model_for_resolves_from_settings() -> None:
    settings = get_settings()
    assert model_for(Provider.GROQ) == settings.groq_model
    assert model_for(Provider.GEMINI) == settings.gemini_model
    assert model_for(Provider.ANTHROPIC) == settings.claude_model


def test_resolve_returns_full_route() -> None:
    route = resolve(Task.FULL_EVALUATION)
    assert route.task is Task.FULL_EVALUATION
    assert route.tier is Tier.QUALITY
    assert route.provider is Provider.ANTHROPIC
    assert route.model == get_settings().claude_model


def test_resolve_for_fast_task_picks_groq_model() -> None:
    route = resolve(Task.INTENT_CLASSIFY)
    assert route.provider is Provider.GROQ
    assert route.model == get_settings().groq_model
