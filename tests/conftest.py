import pytest
import pytest_asyncio
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.db import get_db
from app.core.security import get_current_user
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def protected_test_route():
    """A throwaway protected route (T010) proving get_current_user works
    end-to-end through the real app. Added/removed via a fixture (rather
    than a bare module-level @app.get(...)) so it doesn't permanently mutate
    the shared `app` singleton beyond the test session."""

    @app.get("/_test/protected")
    async def _protected_test_route(user_id: int = Depends(get_current_user)):
        return {"user_id": user_id}

    yield

    app.router.routes = [
        route for route in app.router.routes if getattr(route, "path", None) != "/_test/protected"
    ]


@pytest_asyncio.fixture
async def db_session():
    """A DB session bound to a fresh engine created inside this test's own
    event loop.

    pytest-asyncio gives each test function its own event loop by default,
    but asyncpg connections are bound to the loop that created them — reusing
    the app's module-level engine/session across tests raises "attached to a
    different loop" / "another operation is in progress". Building a
    throwaway engine (NullPool: no pooled connections to go stale) per test
    sidesteps that entirely.
    """
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool, future=True)
    test_session_local = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE"))
        await conn.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))

    async with test_session_local() as session:
        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
