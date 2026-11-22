from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tal.core.config import get_settings
from tal.core.rate_limit import _memory_windows
from tal.db.base import Base
from tal.db.session import get_db_session
from tal.main import app


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[TestClient]:
    monkeypatch.setenv("AUTH_RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setenv("AUTH_RATE_LIMIT_REGISTER_PER_MINUTE", "2")
    get_settings.cache_clear()
    _memory_windows.clear()

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
        _memory_windows.clear()
        await engine.dispose()


def test_register_returns_429_after_limit(client: TestClient) -> None:
    payload = {"email": "rate-limit@example.com", "password": "securepass123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "securepass123"},
    ).status_code == 201
    limited = client.post(
        "/api/v1/auth/register",
        json={"email": "third@example.com", "password": "securepass123"},
    )
    assert limited.status_code == 429
    assert limited.json()["code"] == "rate_limited"
    assert limited.headers.get("retry-after") is not None