"""FastAPI dependencies: database session, authenticated user, services."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.services.auth_service import AuthService
from app.services.metrics_service import MetricsService
from app.services.release_service import ReleaseService
from app.services.repository_service import RepositoryService
from app.services.slack_service import SlackService

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


def get_repository_service(db: DbSession) -> RepositoryService:
    return RepositoryService(db)


def get_release_service(db: DbSession) -> ReleaseService:
    return ReleaseService(db)


def get_slack_service(db: DbSession) -> SlackService:
    return SlackService(db)


def get_metrics_service(db: DbSession) -> MetricsService:
    return MetricsService(db)
