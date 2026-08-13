from collections.abc import AsyncIterator

import pytest
from authlib.integrations.base_client.errors import OAuthError
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tal.db.base import Base
from tal.db.session import get_db_session
from tal.features.auth.oauth import oauth
from tal.main import app


@pytest.fixture
async def client() -> AsyncIterator[TestClient]:
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
        await engine.dispose()


def test_register_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Buddy@Example.COM",
            "password": "securepass123",
        },
    )

    data = response.json()

    assert response.status_code == 201
    assert data["email"] == "buddy@example.com"
    assert data["is_active"] is True
    assert data["id"]
    assert data["created_at"]
    assert data["updated_at"]
    assert "password" not in data
    assert "password_hash" not in data


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    first_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Buddy@Example.COM",
            "password": "securepass123",
        },
    )
    duplicate_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "buddy@example.com",
            "password": "anotherpass123",
        },
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "code": "email_already_registered",
        "message": "Email already registered",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "securepass123"},
        {"email": "buddy@example.com", "password": "short"},
    ],
)
def test_register_rejects_invalid_payload(
    client: TestClient,
    payload: dict[str, str],
) -> None:
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422


class FakeGoogleClient:
    def __init__(self, user_info: dict[str, object]) -> None:
        self.user_info = user_info

    async def authorize_access_token(self, _: object) -> dict[str, object]:
        return {"userinfo": self.user_info}

class FailingGoogleClient:
    async def authorize_access_token(self, _: object) -> dict[str, object]:
        raise OAuthError(error="access_denied")

def test_google_callback_redirects_with_tal_session_cookie(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    google = FakeGoogleClient(
        {
            "sub": "google-user-123",
            "email": "buddy@example.com",
            "email_verified": True,
            "name": "Buddy",
        }
    )
    monkeypatch.setattr(
        oauth,
        "create_client",
        lambda _: google,
    )

    callback_response = client.get(
        "/api/v1/auth/google/callback",
        follow_redirects=False,
    )

    assert callback_response.status_code == 303
    assert (
        callback_response.headers["location"]
        == "http://localhost:3000/"
    )

    set_cookie = callback_response.headers["set-cookie"].lower()

    assert "tal_access_token=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/" in set_cookie
    assert "secure" not in set_cookie

    profile_response = client.get("/api/v1/auth/me")

    assert profile_response.status_code == 200
    assert (
        profile_response.json()["email"]
        == "buddy@example.com"
    )


def test_google_callback_rejects_unverified_email(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    google = FakeGoogleClient(
        {
            "sub": "google-user-123",
            "email": "buddy@example.com",
            "email_verified": False,
        }
    )
    monkeypatch.setattr(oauth, "create_client", lambda _: google)

    response = client.get("/api/v1/auth/google/callback")

    assert response.status_code == 401
    assert response.json() == {
        "code": "invalid_credentials",
        "message": "Invalid credentials",
    }

def test_me_accepts_access_token_cookie(client:TestClient,
                                        monkeypatch:pytest.MonkeyPatch,)->None:
    google=FakeGoogleClient(
        {
        "sub":"google-cookie-user",
        "email":"cookie_@gmail.com",
        "email_verified":True,
    }
    )
    monkeypatch.setattr(oauth,"create_client",lambda _:google)
    callback_response=client.get(
        "/api/v1/auth/google/callback",
        follow_redirects=False,
    )

    assert callback_response.status_code == 303

    response=client.get("/api/v1/auth/me")
    assert response.status_code==200
    assert response.json()["email"]=="cookie_@gmail.com"

def test_logout_clears_access_token_cookie(client:TestClient)->None:
    response=client.post("/api/v1/auth/logout")
    assert response.status_code==204
    set_cookie=response.headers["set-cookie"].lower()
    assert "tal_access_token" in set_cookie
    assert "max-age=0" in set_cookie
    assert "httponly" in set_cookie
    assert "secure" not in set_cookie
    assert "path=/" in set_cookie

def test_google_callback_returns_same_tal_user(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    google = FakeGoogleClient(
        {
            "sub": "returning-google-user",
            "email": "returning@example.com",
            "email_verified": True,
        }
    )
    monkeypatch.setattr(oauth, "create_client", lambda _: google)

    first_callback = client.get(
        "/api/v1/auth/google/callback",
        follow_redirects=False,
    )
    first_profile = client.get("/api/v1/auth/me")

    second_callback = client.get(
        "/api/v1/auth/google/callback",
        follow_redirects=False,
    )
    second_profile = client.get("/api/v1/auth/me")

    assert first_callback.status_code == 303
    assert second_callback.status_code == 303
    assert first_profile.json()["id"] == second_profile.json()["id"]



def test_google_callback_rejects_existing_password_email(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "conflict@example.com",
            "password": "securepass123",
        },
    )
    assert registration.status_code == 201

    google = FakeGoogleClient(
        {
            "sub": "new-google-subject",
            "email": "conflict@example.com",
            "email_verified": True,
        }
    )
    monkeypatch.setattr(oauth, "create_client", lambda _: google)

    response = client.get("/api/v1/auth/google/callback")

    assert response.status_code == 409
    assert response.json()["code"] == "account_link_required"


def test_google_callback_rejects_oauth_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        oauth,
        "create_client",
        lambda _: FailingGoogleClient(),
    )

    response = client.get("/api/v1/auth/google/callback")

    assert response.status_code == 401
    assert response.json() == {
        "code": "invalid_credentials",
        "message": "Invalid credentials",
    }
