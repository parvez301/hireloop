"""Unit tests for the collapsed onboarding state machine.

After 2026-04-22, `_advance_onboarding` transitions `resume_upload → done`
on the presence of a parsed resume alone. The `preferences` intermediate
state is no longer a valid transition target.
"""

from uuid import uuid4

from hireloop.models.profile import Profile
from hireloop.services.profile import _advance_onboarding


def _profile(**overrides: object) -> Profile:
    profile = Profile(user_id=uuid4(), onboarding_state="resume_upload")
    for key, value in overrides.items():
        setattr(profile, key, value)
    return profile


def test_advance_from_resume_upload_to_done_when_resume_parsed() -> None:
    profile = _profile(master_resume_md="# Resume\n\n...content...")
    became_done = _advance_onboarding(profile)
    assert profile.onboarding_state == "done"
    assert became_done is True


def test_advance_does_not_transition_without_resume() -> None:
    profile = _profile()
    became_done = _advance_onboarding(profile)
    assert profile.onboarding_state == "resume_upload"
    assert became_done is False


def test_advance_is_idempotent_on_done_profile() -> None:
    profile = _profile(onboarding_state="done", master_resume_md="# Resume")
    became_done = _advance_onboarding(profile)
    assert profile.onboarding_state == "done"
    assert became_done is False


def test_preferences_data_does_not_block_advancement() -> None:
    """Having roles+locations is no longer needed to reach 'done'."""
    profile = _profile(master_resume_md="# Resume")
    became_done = _advance_onboarding(profile)
    assert profile.onboarding_state == "done"
    assert became_done is True


def test_legacy_preferences_state_advances_if_has_resume() -> None:
    """Legacy profiles left in 'preferences' with a resume self-heal."""
    profile = _profile(onboarding_state="preferences", master_resume_md="# Resume")
    became_done = _advance_onboarding(profile)
    assert profile.onboarding_state == "done"
    assert became_done is True
