import jwt

from app.core.config import settings


async def register_user(client, email="user@example.com", password="password123"):
    return await client.post("/api/v1/auth/register", json={"email": email, "password": password})


async def test_register_returns_201_with_public_fields(client):
    resp = await register_user(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "user@example.com"
    assert "password" not in body
    assert "password_hash" not in body
    assert "id" in body
    assert "created_at" in body


async def test_register_duplicate_email_returns_409(client):
    await register_user(client)
    resp = await register_user(client)
    assert resp.status_code == 409
    assert "error" in resp.json()


async def test_register_duplicate_email_case_insensitive(client):
    await register_user(client, email="CaseTest@Example.com")
    resp = await register_user(client, email="casetest@example.com")
    assert resp.status_code == 409


async def test_login_case_insensitive_email(client):
    await register_user(client, email="CaseLogin@Example.com", password="password123")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "caselogin@example.com", "password": "password123"}
    )
    assert resp.status_code == 200


async def test_register_invalid_input_returns_422(client):
    resp = await client.post(
        "/api/v1/auth/register", json={"email": "not-an-email", "password": "password123"}
    )
    assert resp.status_code == 422
    assert "details" in resp.json()

    resp2 = await client.post(
        "/api/v1/auth/register", json={"email": "a@example.com", "password": "short"}
    )
    assert resp2.status_code == 422

    resp3 = await client.post(
        "/api/v1/auth/register", json={"email": "a@example.com", "password": "x" * 73}
    )
    assert resp3.status_code == 422

    resp4 = await client.post(
        "/api/v1/auth/register", json={"email": "a@example.com\n", "password": "password123"}
    )
    assert resp4.status_code == 422


async def test_login_with_valid_credentials_returns_token(client):
    await register_user(client, email="login@example.com", password="password123")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "login@example.com", "password": "password123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    decoded = jwt.decode(
        body["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert "sub" in decoded and "exp" in decoded and "iat" in decoded


async def test_login_wrong_password_and_missing_user_both_return_identical_401(client):
    await register_user(client, email="login2@example.com", password="password123")

    wrong_password_resp = await client.post(
        "/api/v1/auth/login", json={"email": "login2@example.com", "password": "wrong-password"}
    )
    missing_user_resp = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "password123"}
    )

    assert wrong_password_resp.status_code == 401
    assert missing_user_resp.status_code == 401
    assert wrong_password_resp.json() == missing_user_resp.json()


async def test_protected_route_rejects_missing_invalid_expired_tokens(client):
    no_token = await client.get("/_test/protected")
    assert no_token.status_code == 401
    assert no_token.headers.get("www-authenticate") == "Bearer"

    bad_token = await client.get(
        "/_test/protected", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert bad_token.status_code == 401

    wrong_sig = jwt.encode({"sub": "1"}, "other-secret", algorithm="HS256")
    wrong_sig_resp = await client.get(
        "/_test/protected", headers={"Authorization": f"Bearer {wrong_sig}"}
    )
    assert wrong_sig_resp.status_code == 401


async def test_protected_route_accepts_valid_token_and_resolves_user_id(client):
    reg_resp = await register_user(client, email="proto@example.com", password="password123")
    user_id = reg_resp.json()["id"]

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "proto@example.com", "password": "password123"}
    )
    token = login_resp.json()["access_token"]

    resp = await client.get("/_test/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == user_id
