import pytest

from hireloop.core.evaluation.rule_scorer import SKIPPED, RuleScorer, ScoringContext


@pytest.fixture
def context() -> ScoringContext:
    return ScoringContext(
        profile_skills={"python", "fastapi", "postgres", "kubernetes"},
        profile_years_experience=6,
        profile_target_locations=["remote", "new york"],
        profile_min_salary=140000,
    )


@pytest.fixture
def scorer() -> RuleScorer:
    return RuleScorer()


def test_skills_match_full_overlap(scorer, context):
    job_skills = {"python", "postgres"}
    result = scorer.score_skills_match(job_skills, context)
    assert result.score == 1.0
    assert "python" in result.details


def test_skills_match_no_overlap(scorer, context):
    job_skills = {"ruby", "rails"}
    result = scorer.score_skills_match(job_skills, context)
    assert result.score == 0.0


def test_skills_match_partial_overlap(scorer, context):
    job_skills = {"python", "ruby", "go"}
    result = scorer.score_skills_match(job_skills, context)
    assert 0.3 < result.score < 0.4


def test_experience_fit_exact(scorer, context):
    result = scorer.score_experience_fit(required_years=6, context=context)
    assert result.score == 1.0


def test_experience_fit_over(scorer, context):
    result = scorer.score_experience_fit(required_years=3, context=context)
    assert result.score == 1.0


def test_experience_fit_under_partial(scorer, context):
    result = scorer.score_experience_fit(required_years=10, context=context)
    assert 0.5 < result.score < 0.7


def test_experience_fit_missing_required(scorer, context):
    result = scorer.score_experience_fit(required_years=None, context=context)
    assert result.score == 1.0


def test_location_fit_remote_always_passes(scorer, context):
    result = scorer.score_location_fit(job_location="Remote (US)", context=context)
    assert result.score == 1.0


def test_location_fit_match(scorer, context):
    result = scorer.score_location_fit(job_location="New York, NY", context=context)
    assert result.score == 1.0


def test_location_fit_mismatch(scorer, context):
    result = scorer.score_location_fit(job_location="Tokyo, Japan", context=context)
    assert result.score == 0.0


def test_salary_fit_skipped_when_no_range(scorer, context):
    result = scorer.score_salary_fit(salary_min=None, salary_max=None, context=context)
    assert result is SKIPPED


def test_salary_fit_above_minimum(scorer, context):
    result = scorer.score_salary_fit(salary_min=150000, salary_max=200000, context=context)
    assert result.score == 1.0


def test_salary_fit_below_minimum(scorer, context):
    result = scorer.score_salary_fit(salary_min=90000, salary_max=110000, context=context)
    assert result.score == 0.0
