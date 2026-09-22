from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app.core import security
from app.core.config import settings


def test_hash_and_verify_password_roundtrip():
    password = "correct-horse"
    hashed = security.hash_password(password)
    assert security.verify_password(password, hashed)
    assert not security.verify_password("wrong-password", hashed)


async def test_create_access_token_decodes_to_correct_user_id():
    token, expires_in = security.create_access_token(42)
    assert expires_in == settings.jwt_access_token_expire_minutes * 60

    user_id = await security.get_current_user(token)
    assert user_id == 42


async def test_get_current_user_rejects_expired_token():
    now = datetime.now(timezone.utc)
    payload = {"sub": "1", "iat": now - timedelta(minutes=60), "exp": now - timedelta(minutes=30)}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    with pytest.raises(HTTPException) as exc_info:
        await security.get_current_user(token)
    assert exc_info.value.status_code == 401


async def test_get_current_user_rejects_wrong_signature():
    token = jwt.encode({"sub": "1"}, "a-completely-different-secret", algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        await security.get_current_user(token)
    assert exc_info.value.status_code == 401


async def test_get_current_user_rejects_malformed_token():
    with pytest.raises(HTTPException) as exc_info:
        await security.get_current_user("not-a-jwt-at-all")
    assert exc_info.value.status_code == 401


async def test_get_current_user_rejects_missing_token():
    with pytest.raises(HTTPException) as exc_info:
        await security.get_current_user(None)
    assert exc_info.value.status_code == 401
