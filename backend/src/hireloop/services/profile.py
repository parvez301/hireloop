from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.api.errors import AppError
from hireloop.config import get_settings
from hireloop.core.scanner.default_config import seed_default_scan_config
from hireloop.models.profile import Profile
from hireloop.models.star_story import StarStory
from hireloop.models.user import User
from hireloop.schemas.profile import ProfileUpdate
from hireloop.services.cv_structure_extractor import extract_cv_structure
from hireloop.services.profile_extractor import (
    extract_profile_from_cv,
    merge_extracted_into_profile,
)
from hireloop.services.resume_parser import ResumeParseError, parse_resume_bytes
from hireloop.services.storage import StorageService
from hireloop.services.subscription import ensure_subscription

MAX_RESUME_BYTES = 10 * 1024 * 1024
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}


async def get_or_create_profile(db: AsyncSession, user: User) -> Profile:
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id, onboarding_state="resume_upload")
        db.add(profile)
        await db.flush()
    return profile


def _advance_onboarding(profile: Profile) -> bool:
    """Advance the collapsed onboarding state machine.

    2026-04-22: Preferences collection is no longer part of the gate. A
    profile with a parsed resume transitions directly to 'done'. See
    docs/superpowers/specs/2026-04-22-onboarding-redesign-design.md.

    Returns True if the profile transitioned to the terminal 'done' state
    on this call (i.e. was not 'done' before).
    """
    was_done = profile.onboarding_state == "done"

    has_resume = bool(profile.master_resume_md)

    if profile.onboarding_state in ("resume_upload", "preferences") and has_resume:
        profile.onboarding_state = "done"

    return profile.onboarding_state == "done" and not was_done


async def _on_onboarding_done(db: AsyncSession, profile: Profile) -> None:
    """Hook fired when onboarding transitions to 'done'.

    Materializes the in-app trial row eagerly so admin queries and the
    subscription endpoint see the user as a trialing customer immediately,
    rather than lazily on first entitled request.
    """
    await ensure_subscription(db, profile.user_id, get_settings())
    await seed_default_scan_config(db, profile.user_id)


async def update_profile(
    db: AsyncSession,
    profile: Profile,
    data: ProfileUpdate,
) -> Profile:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    became_done = _advance_onboarding(profile)
    if became_done:
        await _on_onboarding_done(db, profile)

    await db.flush()
    return profile


async def delete_profile_cascade(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.flush()


async def upload_resume(
    db: AsyncSession,
    storage: StorageService,
    profile: Profile,
    filename: str,
    data: bytes,
) -> Profile:
    if len(data) > MAX_RESUME_BYTES:
        raise AppError(413, "PAYLOAD_TOO_LARGE", "Resume exceeds 10MB limit")

    lower = filename.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_RESUME_EXTENSIONS):
        raise AppError(422, "UNPROCESSABLE_ENTITY", "Only PDF and DOCX files are supported")

    try:
        parsed = parse_resume_bytes(data, filename)
    except ResumeParseError as e:
        raise AppError(422, "UNPROCESSABLE_ENTITY", str(e)) from e

    ext = lower[lower.rfind(".") :] if "." in lower else ".pdf"
    s3_key = f"resumes/{profile.user_id}/{uuid4()}{ext}"
    content_type = (
        "application/pdf"
        if lower.endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    await storage.upload_bytes(s3_key, data, content_type=content_type)

    profile.master_resume_s3 = s3_key
    profile.master_resume_md = parsed["markdown"]
    structure = await extract_cv_structure(parsed["markdown"])
    profile.parsed_resume_json = {
        "text": parsed["text"],
        "content_type": parsed["content_type"],
        "structure": structure,
    }

    extracted = await extract_profile_from_cv(parsed["markdown"])
    merge_extracted_into_profile(profile, extracted)

    became_done = _advance_onboarding(profile)
    if became_done:
        await _on_onboarding_done(db, profile)

    await db.flush()
    return profile


async def upload_resume_text(
    db: AsyncSession,
    profile: Profile,
    text: str,
) -> Profile:
    """Store pasted resume text directly as master_resume_md.

    Skips S3 upload and the PDF/DOCX parser — the caller has given us
    markdown-ish text already. Still advances onboarding on success.
    """
    profile.master_resume_md = text
    structure = await extract_cv_structure(text)
    profile.parsed_resume_json = {
        "text": text,
        "content_type": "text/markdown",
        "structure": structure,
    }

    extracted = await extract_profile_from_cv(text)
    merge_extracted_into_profile(profile, extracted)

    became_done = _advance_onboarding(profile)
    if became_done:
        await _on_onboarding_done(db, profile)

    await db.flush()
    return profile


async def export_user_data(db: AsyncSession, user: User) -> dict[str, Any]:
    profile = await get_or_create_profile(db, user)
    story_rows = await db.execute(select(StarStory).where(StarStory.user_id == user.id))
    story_list = story_rows.scalars().all()
    stories = [
        {
            "id": str(s.id),
            "title": s.title,
            "situation": s.situation,
            "task": s.task,
            "action": s.action,
            "result": s.result,
            "reflection": s.reflection,
            "tags": s.tags,
            "source": s.source,
            "created_at": s.created_at.isoformat(),
        }
        for s in story_list
    ]
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "cognito_sub": user.cognito_sub,
            "created_at": user.created_at.isoformat(),
        },
        "profile": {
            "target_roles": profile.target_roles,
            "target_locations": profile.target_locations,
            "min_salary": profile.min_salary,
            "preferred_industries": profile.preferred_industries,
            "linkedin_url": profile.linkedin_url,
            "github_url": profile.github_url,
            "portfolio_url": profile.portfolio_url,
            "master_resume_md": profile.master_resume_md,
            "onboarding_state": profile.onboarding_state,
        },
        "star_stories": stories,
    }
