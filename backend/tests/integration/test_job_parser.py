from pathlib import Path

import pytest
import respx
from httpx import Response

from hireloop.core.evaluation.job_parser import JobParseError, parse_description, parse_url
from tests.fixtures.fake_gemini import fake_gemini

FIXTURE = Path(__file__).parent.parent / "fixtures" / "jobs" / "sample_greenhouse.html"

_FAKE_JSON = (
    '{"title": "Senior Software Engineer, Payments", "company": "Stripe", '
    '"location": "Remote, US", "salary_min": null, "salary_max": null, '
    '"employment_type": "full_time", "seniority": "senior", '
    '"description_md": "We are hiring...", '
    '"requirements": {"skills": ["python", "postgresql", "aws"], '
    '"years_experience": 5, "nice_to_haves": []}}'
)


@pytest.mark.asyncio
async def test_parse_description_success():
    with fake_gemini({"distributed systems": _FAKE_JSON}):
        job = await parse_description(
            "We're hiring a senior engineer to lead distributed systems work. "
            "5+ years experience required."
        )
    assert job.title == "Senior Software Engineer, Payments"
    assert job.company == "Stripe"
    assert "python" in job.requirements_json["skills"]


@pytest.mark.asyncio
@respx.mock
async def test_parse_url_success():
    url = "https://boards.greenhouse.io/stripe/jobs/123"
    html = FIXTURE.read_text()
    respx.get(url).mock(return_value=Response(200, text=html))

    with fake_gemini({"Stripe": _FAKE_JSON}):
        job = await parse_url(url)

    assert job.title == "Senior Software Engineer, Payments"
    assert job.url == url


@pytest.mark.asyncio
@respx.mock
async def test_parse_url_404_raises():
    url = "https://boards.greenhouse.io/stripe/jobs/missing"
    respx.get(url).mock(return_value=Response(404))
    with pytest.raises(JobParseError):
        await parse_url(url)
