"""CV optimizer — Claude Sonnet rewrites a master resume to target a job."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from hireloop.config import get_settings
from hireloop.core.llm.anthropic_client import complete_with_cache
from hireloop.core.llm.errors import LLMParseError

_CACHEABLE_RULES = """You are an expert resume writer optimizing a master resume for a specific job.
Your job is to enhance framing, inject relevant keywords naturally, and reorder content
to highlight relevance. You must NEVER fabricate experience, skills, or results.

RULES:
1. Preserve all factual claims (companies, dates, titles, metrics)
2. Rewrite bullet points to use language/keywords from the JD, but only if the
   underlying claim is already in the master resume
3. Reorder experience bullets within each role to lead with most relevant
4. Rewrite the Summary/Objective section to target this specific role
5. Do NOT add new skills, responsibilities, or certifications
6. Preserve the resume's overall structure (sections, roles, dates)
7. Output the full optimized resume in Markdown format
8. Also output a "changes_summary" explaining what you changed and why"""

_SYSTEM = "You are a precise resume editor. Output only JSON — never prose outside JSON."


@dataclass
class OptimizationResult:
    tailored_md: str
    changes_summary: str
    keywords_injected: list[str]
    sections_reordered: list[str]
    usage: Any
    model: str


class CvOptimizer:
    async def rewrite(
        self,
        *,
        master_resume_md: str,
        job_markdown: str,
        keywords: list[str],
        additional_feedback: str | None,
    ) -> OptimizationResult:
        settings = get_settings()
        user_block = self._build_user_block(
            master_resume_md, job_markdown, keywords, additional_feedback
        )
        result = await complete_with_cache(
            system=_SYSTEM,
            cacheable_blocks=[_CACHEABLE_RULES],
            user_block=user_block,
            model=settings.claude_model,
            max_tokens=4000,
            timeout_s=settings.llm_cv_optimize_timeout_s,
        )
        parsed = self._parse(result.text)
        return OptimizationResult(
            tailored_md=parsed["tailored_md"],
            changes_summary=parsed.get("changes_summary", ""),
            keywords_injected=list(parsed.get("keywords_injected", [])),
            sections_reordered=list(parsed.get("sections_reordered", [])),
            usage=result.usage,
            model=result.model,
        )

    @staticmethod
    def _build_user_block(
        master_resume_md: str,
        job_markdown: str,
        keywords: list[str],
        additional_feedback: str | None,
    ) -> str:
        fb = (
            f"\n\nADDITIONAL FEEDBACK FROM USER:\n{additional_feedback}"
            if additional_feedback
            else ""
        )
        return (
            "INPUT MASTER RESUME (Markdown):\n"
            f"{master_resume_md}\n\n"
            "TARGET JOB DESCRIPTION:\n"
            f"{job_markdown}\n\n"
            "TARGETED KEYWORDS (from JD analysis):\n"
            f"{', '.join(keywords)}"
            f"{fb}\n\n"
            "OUTPUT JSON:\n"
            "{\n"
            '  "tailored_md": "...full optimized resume markdown...",\n'
            '  "changes_summary": "Short bullet list of what was changed and why",\n'
            '  "keywords_injected": ["keyword1", "keyword2"],\n'
            '  "sections_reordered": ["Experience bullets in Role A", ...]\n'
            "}"
        )

    @staticmethod
    def _parse(text: str) -> dict[str, Any]:
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMParseError(
                "CV optimizer returned invalid JSON",
                provider="anthropic",
                details={"raw": raw[:500]},
            ) from e
        if "tailored_md" not in data:
            raise LLMParseError(
                "Missing 'tailored_md' field in optimizer response",
                provider="anthropic",
            )
        return data
