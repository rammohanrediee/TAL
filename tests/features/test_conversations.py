from collections.abc import AsyncIterator

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tal.core.config import settings
from tal.db.base import Base
from tal.db.session import get_db_session
from tal.features.auth.dependencies import get_current_user
from tal.features.auth.entities import User
from tal.features.conversations.entities import Conversation  # noqa: F401
from tal.main import app


@pytest.mark.asyncio
async def test_conversation_is_owned_and_token_is_scoped() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as session:
        owner = User(email="chat-owner@example.com")
        stranger = User(email="chat-stranger@example.com")
        session.add_all([owner, stranger])
        await session.commit()
        await session.refresh(owner)
        await session.refresh(stranger)

    async def db() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    async def current_user() -> User:
        return owner

    app.dependency_overrides[get_db_session] = db
    app.dependency_overrides[get_current_user] = current_user
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/conversations/")
            assert created.status_code == 201
            conversation_id = created.json()["id"]
            assert len(client.get("/api/v1/conversations/").json()) == 1

            token_response = client.post(
                f"/api/v1/conversations/{conversation_id}/connection-token"
            )
            assert token_response.status_code == 200
            claims = jwt.decode(
                token_response.json()["token"],
                settings.jwt_secret_key.get_secret_value(),
                algorithms=["HS256"],
                audience="tal-chat",
            )
            assert claims["sub"] == str(owner.id)
            assert claims["cid"] == conversation_id

            app.dependency_overrides[get_current_user] = lambda: stranger
            assert client.get("/api/v1/conversations/").json() == []
            assert client.post(
                f"/api/v1/conversations/{conversation_id}/connection-token"
            ).status_code == 404
            assert client.delete(f"/api/v1/conversations/{conversation_id}").status_code == 404

            app.dependency_overrides[get_current_user] = current_user
            assert client.delete(f"/api/v1/conversations/{conversation_id}").status_code == 204
            assert client.get("/api/v1/conversations/").json() == []
            assert client.post(
                f"/api/v1/conversations/{conversation_id}/connection-token"
            ).status_code == 404
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
