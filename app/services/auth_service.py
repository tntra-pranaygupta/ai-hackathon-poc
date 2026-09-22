from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateEmailError, InvalidCredentialsError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password_async,
    verify_password_async,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)

    async def register(self, data: UserCreate) -> User:
        existing = await self.repo.get_by_email(data.email)
        if existing is not None:
            raise DuplicateEmailError()

        password_hash = await hash_password_async(data.password)
        try:
            user = await self.repo.create(email=data.email, password_hash=password_hash)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise DuplicateEmailError()
        await self.session.refresh(user)
        return user

    async def login(self, email: str, password: str) -> tuple[str, int]:
        user = await self.repo.get_by_email(email)
        if user is None:
            # Timing-safe: still do a bcrypt comparison against a fixed
            # dummy hash so this path costs about the same as the found case.
            await verify_password_async(password, DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError()

        if not await verify_password_async(password, user.password_hash):
            raise InvalidCredentialsError()

        token, expires_in = create_access_token(user.id)
        return token, expires_in
