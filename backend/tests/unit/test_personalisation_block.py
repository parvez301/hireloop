"""Tests for the anti-generic personalisation block (Layer 5).

Locks in:
- Banned phrases list matches the spec doc verbatim
- with_personalisation() is idempotent and appends correctly
- All four generator system prompts include the block (regression guard so
  nobody silently strips it during a future refactor)
"""

from __future__ import annotations

from hireloop.core.cv_optimizer.optimizer import _SYSTEM as CV_OPTIMIZER_SYSTEM
from hireloop.core.evaluation.claude_scorer import _SYSTEM as EVALUATION_SYSTEM
from hireloop.core.interview_prep.generator import _SYSTEM as INTERVIEW_PREP_SYSTEM
from hireloop.core.llm.personalisation import (
    BANNED_PHRASES,
    PERSONALISATION_BLOCK,
    with_personalisation,
)
from hireloop.core.negotiation.playbook import _SYSTEM as NEGOTIATION_SYSTEM


def test_banned_phrases_matches_spec_doc() -> None:
    # Verbatim list from PERSONALISATION_STRATEGY.md lines 363-376. If the
    # spec changes, update both the constant and this test together.
    assert BANNED_PHRASES == (
        "consider highlighting",
        "you may want to",
        "your experience aligns",
        "strong background",
        "leverage your skills",
        "results-driven",
        "team player",
        "passionate about",
        "proven track record",
        "detail-oriented",
        "go-getter",
        "dynamic professional",
    )


def test_block_includes_every_banned_phrase() -> None:
    for phrase in BANNED_PHRASES:
        assert phrase in PERSONALISATION_BLOCK, (
            f"Banned phrase {phrase!r} missing from PERSONALISATION_BLOCK"
        )


def test_block_includes_six_numbered_rules() -> None:
    for n in range(1, 7):
        assert f"{n}." in PERSONALISATION_BLOCK


def test_with_personalisation_appends_block() -> None:
    result = with_personalisation("You are a resume editor.")
    assert result.startswith("You are a resume editor.")
    assert PERSONALISATION_BLOCK in result


def test_with_personalisation_is_idempotent() -> None:
    once = with_personalisation("base")
    twice = with_personalisation(once)
    assert once == twice
    assert twice.count("PERSONALISATION RULES") == 1


def test_with_personalisation_preserves_empty_input() -> None:
    result = with_personalisation("")
    assert result == PERSONALISATION_BLOCK


def test_cv_optimizer_system_prompt_includes_block() -> None:
    assert PERSONALISATION_BLOCK in CV_OPTIMIZER_SYSTEM


def test_evaluation_system_prompt_includes_block() -> None:
    assert PERSONALISATION_BLOCK in EVALUATION_SYSTEM


def test_negotiation_system_prompt_includes_block() -> None:
    assert PERSONALISATION_BLOCK in NEGOTIATION_SYSTEM


def test_interview_prep_system_prompt_includes_block() -> None:
    assert PERSONALISATION_BLOCK in INTERVIEW_PREP_SYSTEM
