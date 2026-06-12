from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.logging import audit_log
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.users import UserRepository
from app.schemas.auth import UserLogin, UserRegister


class AuthService:
    def __init__(self, session: Session) -> None:
        self.users = UserRepository(session)

    def register(self, payload: UserRegister) -> User:
        email = payload.email.lower()
        if self.users.get_by_email(email):
            raise ConflictError("A user with this email already exists")
        user = self.users.add(
            User(
                email=email,
                hashed_password=hash_password(payload.password),
                full_name=payload.full_name,
            )
        )
        self.users.commit()
        audit_log("user_registered", user_id=user.id, email=email)
        return user

    def login(self, payload: UserLogin) -> str:
        user = self.users.get_by_email(payload.email)
        if not user or not user.is_active or not verify_password(
            payload.password, user.hashed_password
        ):
            audit_log("login_failed", email=payload.email.lower())
            raise UnauthorizedError("Invalid email or password")
        audit_log("login_succeeded", user_id=user.id)
        return create_access_token(str(user.id))
