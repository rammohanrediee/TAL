from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tal.core.config import get_settings
from tal.db.base import Base
from tal.db.session import get_db_session
from tal.main import app


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[TestClient]:
    monkeypatch.setenv("AUTH_CSRF_ENABLED", "true")
    monkeypatch.setenv("AUTH_RATE_LIMIT_BACKEND", "memory")
    get_settings.cache_clear()

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        await engine.dispose()


def test_csrf_blocks_cookie_session_mutations_without_header(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "csrf@example.com", "password": "securepass123"},
    )
    client.post(
        "/api/v1/auth/token",
        data={"username": "csrf@example.com", "password": "securepass123"},
    )
    assert client.cookies.get("tal_csrf")

    blocked = client.post("/api/v1/conversations")
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "csrf_failed"

    allowed = client.post(
        "/api/v1/conversations",
        headers={"X-CSRF-Token": client.cookies["tal_csrf"]},
    )
    assert allowed.status_code == 201