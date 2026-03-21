from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.users.schemas import UserPublic

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)
