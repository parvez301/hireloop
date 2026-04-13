from hireloop.core.batch.l0_filter import l0_filter
from hireloop.models.job import Job
from hireloop.models.profile import Profile


def _job(**overrides) -> Job:
    defaults = dict(
        content_hash="test_" + str(id(object())),
        title="Test",
        description_md="x",
        requirements_json={},
        source="manual",
        location="Remote",
        salary_min=None,
        salary_max=None,
        seniority="senior",
    )
    defaults.update(overrides)
    return Job(**defaults)


def _profile(**overrides) -> Profile:
    defaults = dict(
        user_id="00000000-0000-0000-0000-000000000001",
        onboarding_state="done",
        target_roles=["senior engineer"],
        target_locations=["remote", "new york"],
        min_salary=150000,
        parsed_resume_json={"total_years_experience": 6, "skills": ["python"]},
    )
    defaults.update(overrides)
    p = Profile()
    for k, v in defaults.items():
        setattr(p, k, v)
    return p


def test_passes_remote_job() -> None:
    passes, reason = l0_filter(_job(location="Remote"), _profile())
    assert passes is True
    assert reason is None


def test_passes_target_location() -> None:
    passes, reason = l0_filter(_job(location="New York, NY"), _profile())
    assert passes is True


def test_filters_location_mismatch() -> None:
    passes, reason = l0_filter(_job(location="Tokyo"), _profile())
    assert passes is False
    assert reason == "location_mismatch"


def test_filters_salary_below_floor() -> None:
    passes, reason = l0_filter(
        _job(salary_min=80000, salary_max=110000), _profile(min_salary=150000)
    )
    assert passes is False
    assert reason == "below_min_salary"


def test_passes_when_salary_not_posted() -> None:
    passes, reason = l0_filter(_job(salary_min=None, salary_max=None), _profile())
    assert passes is True


def test_passes_when_no_min_salary_set() -> None:
    passes, reason = l0_filter(
        _job(salary_min=80000, salary_max=90000), _profile(min_salary=None)
    )
    assert passes is True


def test_filters_seniority_mismatch_principal_vs_junior() -> None:
    passes, reason = l0_filter(
        _job(seniority="principal"),
        _profile(parsed_resume_json={"total_years_experience": 1, "skills": []}),
    )
    assert passes is False
    assert reason == "seniority_mismatch"


def test_passes_when_seniority_missing() -> None:
    passes, reason = l0_filter(_job(seniority=None), _profile())
    assert passes is True
