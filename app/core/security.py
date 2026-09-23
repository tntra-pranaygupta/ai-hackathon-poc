"""Shared security module.

Owned by the user-auth feature, consumed by product-crud (and any future
feature) via `get_current_user`. See specs/user-auth/plan.md ADR-3.
"""

from datetime import datetime, timedelta, timezone

import anyio
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

bearer_scheme = HTTPBearer(auto_error=False)

# Fixed, precomputed dummy hash used to keep login timing comparable when the
# looked-up email does not exist (specs/user-auth/plan.md Risks section).
# Computed once at import time from a constant string — never per request.
DUMMY_PASSWORD_HASH = pwd_context.hash("dummy-password-for-timing-safety")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


async def hash_password_async(password: str) -> str:
    """bcrypt is CPU-bound (~100-300ms); run it off the event loop so one
    registration doesn't stall every other in-flight request."""
    return await anyio.to_thread.run_sync(hash_password, password)


async def verify_password_async(password: str, password_hash: str) -> bool:
    return await anyio.to_thread.run_sync(verify_password, password, password_hash)


def create_access_token(user_id: int) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expire_minutes = settings.jwt_access_token_expire_minutes
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expire_minutes)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expire_minutes * 60


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    """FastAPI dependency: decodes the bearer JWT and returns the user id.

    Raises 401 if the token is missing, malformed, expired, or has an
    invalid signature. Does not hit the database.
    """
    if credentials is None:
        raise _unauthorized()
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        raise _unauthorized()

    sub = payload.get("sub")
    if sub is None:
        raise _unauthorized()
    try:
        return int(sub)
    except (TypeError, ValueError):
        raise _unauthorized()
