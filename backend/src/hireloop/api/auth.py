from fastapi import APIRouter

from hireloop.api.deps import CurrentDbUser, DbSession
from hireloop.schemas.common import Envelope
from hireloop.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=Envelope[UserResponse])
async def me(user: CurrentDbUser, db: DbSession) -> Envelope[UserResponse]:
    _ = db
    return Envelope(data=UserResponse.model_validate(user))
