from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import CurrentUser, get_auth_service
from app.core.config import get_settings
from app.core.ratelimit import limiter
from app.schemas.auth import TokenOut, UserLogin, UserOut, UserRegister
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

AuthSvc = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_settings().rate_limit_auth)
def register(request: Request, payload: UserRegister, service: AuthSvc) -> UserOut:
    return UserOut.model_validate(service.register(payload))


@router.post("/login", response_model=TokenOut)
@limiter.limit(get_settings().rate_limit_auth)
def login(request: Request, payload: UserLogin, service: AuthSvc) -> TokenOut:
    return TokenOut(access_token=service.login(payload))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
