"""Parse a job posting from URL or raw text into a structured form."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup

from hireloop.core.llm.errors import LLMError
from hireloop.core.llm.fast_client import extract_json


class JobParseError(Exception):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details: dict[str, Any] = details or {}


@dataclass
class ParsedJob:
    title: str
    company: str | None
    location: str | None
    salary_min: int | None
    salary_max: int | None
    employment_type: str | None
    seniority: str | None
    description_md: str
    requirements_json: dict[str, Any]
    url: str | None = None

    @property
    def content_hash(self) -> str:
        payload = json.dumps(
            {
                "description": self.description_md.strip(),
                "requirements": self.requirements_json,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


_EXTRACT_PROMPT = """Extract the following fields from this job posting as strict JSON. Output ONLY JSON, no prose.

Schema:
{{
  "title": string,
  "company": string or null,
  "location": string or null,
  "salary_min": integer or null,
  "salary_max": integer or null,
  "employment_type": "full_time" | "part_time" | "contract" | null,
  "seniority": "junior" | "mid" | "senior" | "staff" | "principal" | null,
  "description_md": string,
  "requirements": {{
    "skills": [string],
    "years_experience": integer or null,
    "nice_to_haves": [string]
  }}
}}

Job posting:
{body}

JSON:"""


async def parse_description(description_md: str) -> ParsedJob:
    if not description_md or len(description_md.strip()) < 50:
        raise JobParseError("Description too short to parse")
    return await _extract(description_md[:8000], url=None)


async def parse_url(url: str) -> ParsedJob:
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "HireLoop/1.0 (+https://careeragent.com/bot)"},
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as e:
        raise JobParseError(f"Failed to fetch URL: {e}", details={"url": url}) from e

    if resp.status_code >= 400:
        raise JobParseError(
            f"URL returned HTTP {resp.status_code}",
            details={"url": url, "status": resp.status_code},
        )

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    if len(text) < 100:
        raise JobParseError("Page has too little text — may require JS", details={"url": url})

    return await _extract(text[:8000], url=url)


async def _extract(body: str, *, url: str | None) -> ParsedJob:
    prompt = _EXTRACT_PROMPT.format(body=body)
    try:
        data = await extract_json(prompt, timeout_s=10.0)
    except LLMError as e:
        raise JobParseError(f"Structured extraction failed: {e}") from e

    if not data.get("title"):
        raise JobParseError("Extraction returned no title")

    return ParsedJob(
        title=str(data["title"]),
        company=data.get("company"),
        location=data.get("location"),
        salary_min=data.get("salary_min"),
        salary_max=data.get("salary_max"),
        employment_type=data.get("employment_type"),
        seniority=data.get("seniority"),
        description_md=str(data.get("description_md") or body),
        requirements_json=data.get("requirements") or {"skills": []},
        url=url,
    )
