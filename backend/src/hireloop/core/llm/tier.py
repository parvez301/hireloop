"""LLM tier + provider taxonomy and task→tier→model routing.

Source of truth: ~/Downloads/MODEL_ROUTING_STRATEGY.md (HireLoop only — logistics
use case dropped). Three tiers:

- FAST     : Groq Llama 3.1 8B          — classification, routing, extraction
- BALANCED : Gemini 2.0 Flash           — summarisation, drafting, scoring
- QUALITY  : Claude Sonnet 4.6 (direct) — writing, reasoning, user-facing output

The `Task` enum lists every named LLM call site in HireLoop. Adding a new call
site means adding a Task value and registering its tier in `_TASK_TIER`. The
router (router.py) is the only place that should map task → provider + model.
"""

from __future__ import annotations

from enum import StrEnum

from hireloop.config import get_settings


class Tier(StrEnum):
    FAST = "fast"
    BALANCED = "balanced"
    QUALITY = "quality"


class Provider(StrEnum):
    GROQ = "groq"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class Task(StrEnum):
    # FAST — Groq Llama 3.1 8B
    INTENT_CLASSIFY = "intent_classify"
    JOB_CLASSIFY = "job_classify"
    JOB_DEDUP = "job_dedup"
    SALARY_EXTRACT = "salary_extract"
    JD_ENTITY_EXTRACT = "jd_entity_extract"
    SESSION_TRIGGER = "session_trigger"
    YES_NO_PRESCREEN = "yes_no_prescreen"

    # BALANCED — Gemini 2.0 Flash
    CV_STRUCTURE_EXTRACT = "cv_structure_extract"
    PROFILE_EXTRACT = "profile_extract"
    QUICK_FIT_SCORE = "quick_fit_score"
    GAP_SUMMARY = "gap_summary"
    INTERVIEW_QUESTIONS = "interview_questions"
    LINKEDIN_MESSAGE = "linkedin_message"
    APPLICATION_FORM_ANSWERS = "application_form_answers"
    PDF_STRUCTURE = "pdf_structure"
    JOB_TITLE_NORMALISE = "job_title_normalise"
    CROSSREF_MAP = "crossref_map"

    # QUALITY — Claude Sonnet 4.6 direct
    FULL_EVALUATION = "full_evaluation"
    STAR_STORY = "star_story"
    CV_REWRITE = "cv_rewrite"
    COVER_LETTER = "cover_letter"
    NEGOTIATION_SCRIPT = "negotiation_script"
    SMART_APPLY_CV = "smart_apply_cv"
    SMART_APPLY_COVER = "smart_apply_cover"


_TASK_TIER: dict[Task, Tier] = {
    # FAST
    Task.INTENT_CLASSIFY: Tier.FAST,
    Task.JOB_CLASSIFY: Tier.FAST,
    Task.JOB_DEDUP: Tier.FAST,
    Task.SALARY_EXTRACT: Tier.FAST,
    Task.JD_ENTITY_EXTRACT: Tier.FAST,
    Task.SESSION_TRIGGER: Tier.FAST,
    Task.YES_NO_PRESCREEN: Tier.FAST,
    # BALANCED
    Task.CV_STRUCTURE_EXTRACT: Tier.BALANCED,
    Task.PROFILE_EXTRACT: Tier.BALANCED,
    Task.QUICK_FIT_SCORE: Tier.BALANCED,
    Task.GAP_SUMMARY: Tier.BALANCED,
    Task.INTERVIEW_QUESTIONS: Tier.BALANCED,
    Task.LINKEDIN_MESSAGE: Tier.BALANCED,
    Task.APPLICATION_FORM_ANSWERS: Tier.BALANCED,
    Task.PDF_STRUCTURE: Tier.BALANCED,
    Task.JOB_TITLE_NORMALISE: Tier.BALANCED,
    Task.CROSSREF_MAP: Tier.BALANCED,
    # QUALITY
    Task.FULL_EVALUATION: Tier.QUALITY,
    Task.STAR_STORY: Tier.QUALITY,
    Task.CV_REWRITE: Tier.QUALITY,
    Task.COVER_LETTER: Tier.QUALITY,
    Task.NEGOTIATION_SCRIPT: Tier.QUALITY,
    Task.SMART_APPLY_CV: Tier.QUALITY,
    Task.SMART_APPLY_COVER: Tier.QUALITY,
}


_TIER_PROVIDER: dict[Tier, Provider] = {
    Tier.FAST: Provider.GROQ,
    Tier.BALANCED: Provider.GEMINI,
    Tier.QUALITY: Provider.ANTHROPIC,
}


def tier_for(task: Task) -> Tier:
    return _TASK_TIER[task]


def provider_for(tier: Tier) -> Provider:
    return _TIER_PROVIDER[tier]


def model_for(provider: Provider) -> str:
    """Resolve provider → model id from settings.

    Centralised so model upgrades only touch config.py.
    """
    settings = get_settings()
    if provider is Provider.GROQ:
        return settings.groq_model
    if provider is Provider.GEMINI:
        return settings.gemini_model
    return settings.claude_model
