from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, email: str, password_hash: str) -> User:
        # Flush (not commit) — the service layer owns the transaction
        # boundary so it can coordinate multiple repository calls in one
        # unit of work as the app grows.
        user = User(email=email, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        return user
