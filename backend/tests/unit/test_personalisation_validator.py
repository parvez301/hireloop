"""Unit tests for the Layer-6 personalisation validator (pure-function path)."""

from __future__ import annotations

from typing import Any

from hireloop.services.personalisation_validator import validate

_CV: dict[str, Any] = {
    "roles": [
        {"title": "Senior Engineer", "company": "Stripe", "key_achievements": ["X"]},
        {"title": "Engineer", "company": "RSA Global", "key_achievements": ["Y"]},
    ],
    "notable_numbers": [
        "Reduced billing errors by 40%",
        "Managed team of 12 across 3 countries",
    ],
}
_JD: dict[str, Any] = {"company": "Acme Corp", "title": "Staff Engineer"}


def test_passes_when_all_three_checks_satisfied() -> None:
    output = (
        "Your work at Stripe and Reduced billing errors by 40% align directly "
        "with what Acme Corp is looking for in this role."
    )
    report = validate(output, _CV, _JD)
    assert report.passed is True
    assert report.generic_phrases_found == []
    assert report.mentions_company is True
    assert report.specific_cv_facts_referenced >= 2


def test_fails_on_banned_phrase() -> None:
    output = (
        "You may want to highlight your work at Stripe. Your strong background "
        "in payments matches Acme Corp's needs."
    )
    report = validate(output, _CV, _JD)
    assert report.passed is False
    assert "you may want to" in report.generic_phrases_found
    assert "strong background" in report.generic_phrases_found


def test_fails_when_company_not_mentioned() -> None:
    output = "Your Stripe and RSA Global experience map to this role."
    report = validate(output, _CV, _JD)
    assert report.passed is False
    assert report.mentions_company is False


def test_fails_when_fewer_than_two_cv_facts() -> None:
    output = "Your work at Stripe is great for Acme Corp."
    report = validate(output, _CV, _JD)
    assert report.passed is False
    assert report.specific_cv_facts_referenced == 1


def test_company_check_skipped_when_jd_has_no_company() -> None:
    output = "Your Stripe and RSA Global work fits this role."
    report = validate(output, _CV, {})
    # Company check passes by default when no company is on the JD.
    assert report.mentions_company is True
    assert report.passed is True
    assert report.specific_cv_facts_referenced >= 2


def test_handles_missing_cv_structure() -> None:
    report = validate("Generic Acme Corp output", None, _JD)
    assert report.passed is False
    assert report.specific_cv_facts_referenced == 0


def test_case_insensitive_match() -> None:
    output = "your STRIPE work and REDUCED BILLING ERRORS BY 40% are perfect for acme corp"
    report = validate(output, _CV, _JD)
    assert report.passed is True
    assert report.specific_cv_facts_referenced >= 2
