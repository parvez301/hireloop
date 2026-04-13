from typing import Annotated, Any

from fastapi import APIRouter, Depends, UploadFile

from hireloop.api.deps import CurrentDbUser, DbSession
from hireloop.schemas.common import Envelope
from hireloop.schemas.profile import ProfileResponse, ProfileUpdate
from hireloop.services.profile import (
    delete_profile_cascade,
    export_user_data,
    get_or_create_profile,
    update_profile,
    upload_resume,
)
from hireloop.services.storage import StorageService, get_storage_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=Envelope[ProfileResponse])
async def get_profile(user: CurrentDbUser, db: DbSession) -> Envelope[ProfileResponse]:
    profile = await get_or_create_profile(db, user)
    await db.refresh(profile)
    return Envelope(data=ProfileResponse.model_validate(profile))


@router.put("", response_model=Envelope[ProfileResponse])
async def put_profile(
    data: ProfileUpdate,
    user: CurrentDbUser,
    db: DbSession,
) -> Envelope[ProfileResponse]:
    profile = await get_or_create_profile(db, user)
    profile = await update_profile(db, profile, data)
    await db.refresh(profile)
    return Envelope(data=ProfileResponse.model_validate(profile))


@router.delete("", status_code=204)
async def delete_profile(user: CurrentDbUser, db: DbSession) -> None:
    await delete_profile_cascade(db, user)


@router.post("/resume", response_model=Envelope[ProfileResponse])
async def upload_resume_endpoint(
    file: UploadFile,
    user: CurrentDbUser,
    db: DbSession,
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> Envelope[ProfileResponse]:
    contents = await file.read()
    profile = await get_or_create_profile(db, user)
    profile = await upload_resume(db, storage, profile, file.filename or "resume.pdf", contents)
    await db.refresh(profile)
    return Envelope(data=ProfileResponse.model_validate(profile))


@router.post("/export", response_model=Envelope[dict[str, Any]])
async def export_profile(user: CurrentDbUser, db: DbSession) -> Envelope[dict[str, Any]]:
    data = await export_user_data(db, user)
    return Envelope(data=data)
