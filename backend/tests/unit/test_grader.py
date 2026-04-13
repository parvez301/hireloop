import pytest

from hireloop.core.evaluation.grader import Grader
from hireloop.core.evaluation.rule_scorer import SKIPPED, DimensionResult


@pytest.fixture
def grader() -> Grader:
    return Grader()


def _perfect_rule_dims() -> dict:
    return {
        "skills_match": DimensionResult(score=1.0),
        "experience_fit": DimensionResult(score=1.0),
        "location_fit": DimensionResult(score=1.0),
        "salary_fit": DimensionResult(score=1.0),
    }


def _perfect_claude_dims() -> dict:
    return {
        "domain_relevance": {"score": 1.0, "grade": "A", "reasoning": "", "signals": []},
        "role_match": {"score": 1.0, "grade": "A", "reasoning": "", "signals": []},
        "trajectory_fit": {"score": 1.0, "grade": "A", "reasoning": "", "signals": []},
        "culture_signal": {"score": 1.0, "grade": "A", "reasoning": "", "signals": []},
        "red_flags": {"score": 1.0, "grade": "A", "reasoning": "", "signals": []},
        "growth_potential": {"score": 1.0, "grade": "A", "reasoning": "", "signals": []},
    }


def test_perfect_score_maps_to_grade_a(grader):
    result = grader.aggregate(
        rule_dims=_perfect_rule_dims(),
        claude_dims=_perfect_claude_dims(),
        overall_reasoning="Strong fit",
        red_flag_items=[],
        personalization_notes=None,
    )
    assert result.overall_grade == "A"
    assert result.match_score == 1.0
    assert result.recommendation == "strong_match"


def test_zero_score_maps_to_grade_f(grader):
    rule = {k: DimensionResult(score=0.0) for k in _perfect_rule_dims()}
    claude = {
        k: {"score": 0.0, "grade": "F", "reasoning": "", "signals": []}
        for k in _perfect_claude_dims()
    }
    result = grader.aggregate(
        rule_dims=rule,
        claude_dims=claude,
        overall_reasoning="No match",
        red_flag_items=[],
        personalization_notes=None,
    )
    assert result.overall_grade == "F"
    assert result.recommendation == "skip"


def test_salary_skipped_redistributes_weight(grader):
    rule = _perfect_rule_dims()
    rule["salary_fit"] = SKIPPED
    result = grader.aggregate(
        rule_dims=rule,
        claude_dims=_perfect_claude_dims(),
        overall_reasoning="",
        red_flag_items=[],
        personalization_notes=None,
    )
    assert result.match_score == pytest.approx(1.0, abs=0.001)


def test_grade_boundaries(grader):
    mapping = [
        (0.95, "A"),
        (0.92, "A"),
        (0.88, "A-"),
        (0.80, "B+"),
        (0.74, "B"),
        (0.64, "B-"),
        (0.55, "C+"),
        (0.45, "C"),
        (0.35, "D"),
        (0.20, "F"),
    ]
    for score, expected in mapping:
        assert grader._map_to_letter(score) == expected, f"{score} should be {expected}"


def test_recommendation_from_grade(grader):
    assert grader._recommendation("A") == "strong_match"
    assert grader._recommendation("A-") == "strong_match"
    assert grader._recommendation("B+") == "worth_exploring"
    assert grader._recommendation("B") == "worth_exploring"
    assert grader._recommendation("B-") == "worth_exploring"
    assert grader._recommendation("C+") == "skip"
    assert grader._recommendation("F") == "skip"
