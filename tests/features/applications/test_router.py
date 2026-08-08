from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tal.db.base import Base
from tal.db.session import get_db_session
from tal.features.auth.dependencies import get_current_user
from tal.main import app
from tal.features.auth.entities import User
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture
async def client() -> AsyncIterator[TestClient]:
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async  with TestSessionFactory() as session:
        current_user=User(email="owner@example.com")
        session.add(current_user)
        await session.commit()

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with TestSessionFactory() as session:
            yield session
    async def override_get_current_user() -> User:
        return current_user

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_current_user]=override_get_current_user

    yield TestClient(app)

    app.dependency_overrides.clear()




def test_create_application(client: TestClient) -> None:

    response = client.post(
        "/api/v1/applications/",
        json={
            "company_name": "OpenAI",
            "role_title": "Backend Engineer",
            "job_url": "https://openAI.com",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["company_name"] == "OpenAI"
    assert data["role_title"] == "Backend Engineer"
    assert data["status"] == "saved"
    assert data["job_url"] == "https://openai.com/"
    assert "created_at" in data
    assert "updated_at" in data
    assert data["id"]


def test_application_validation(client: TestClient) -> None:
    response = client.post(
        "/api/v1/applications",
        json={
            "role_title": "Back Engineer",
        },
    )
    assert response.status_code == 422


def test_list_application(client: TestClient) -> None:
    client.post(
        "/api/v1/applications/",
        json={
            "company_name": "openAI",
            "role_title": "Backend Enginner",
            "job_url": "https://openai.com/job",
        },
    )
    response = client.get("/api/v1/applications/")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["company_name"] == "openAI"
    assert data[0]["role_title"] == "Backend Enginner"
    assert data[0]["status"] == "saved"
    assert data[0]["job_url"] == "https://openai.com/job"


def test_get_application_not_found(client: TestClient) -> None:
    missing_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/applications/{missing_id}")
    data = response.json()
    assert response.status_code == 404
    assert data["code"] == "application_not_found"
    assert "Application not found" in data["message"]


def test_get_application_by_id(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/applications/",
        json={
            "company_name": "openAI",
            "role_title": "Backend Engineer",
            "job_url": "https://openai.com/job",
        },
    )
    created = create_response.json()
    assert create_response.status_code == 200
    id = created["id"]
    response = client.get(f"/api/v1/applications/{id}")
    data = response.json()
    assert data["id"] == id
    assert data["company_name"] == "openAI"
    assert data["role_title"] == "Backend Engineer"
    assert data["status"] == "saved"
    assert data["job_url"] == "https://openai.com/job"


def test_update_application_status(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/applications/",
        json={
            "company_name": "openAI",
            "role_title": "Backend Engineer",
        },
    )
    application_id = create_response.json()["id"]
    response = client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "applied"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == application_id
    assert data["status"] == "applied"
    get_response = client.get(f"/api/v1/applications/{application_id}")
    assert get_response.json()["status"] == "applied"



@pytest.fixture
async def other_user(client: TestClient) -> User:
    async with TestSessionFactory() as session:
        user = User(email="other@example.com")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

def test_get_application_hides_foreign_application(
    client: TestClient,
    other_user: User,
) -> None:
    create_response = client.post(
        "/api/v1/applications/",
        json={
            "company_name": "OpenAI",
            "role_title": "Backend Engineer",
        },
    )
    assert create_response.status_code == 200
    application_id = create_response.json()["id"]

    async def override_get_current_user() -> User:
        return other_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = client.get(f"/api/v1/applications/{application_id}")
    data = response.json()

    assert response.status_code == 404
    assert data["code"] == "application_not_found"


def test_update_application_hides_foreign_application(
        client:TestClient,
        other_user:User,
)->None:
    create_response=client.post(
        "/api/v1/applications/",
        json={
            "company_name":"OpenAI",
            "role_title":"Backend Engineer",
        },
    )
    assert create_response.status_code==200
    application_id=create_response.json()["id"]

    owner_override=app.dependency_overrides[get_current_user]

    async def override_get_current_user() -> User:
        return other_user
    app.dependency_overrides[get_current_user]=override_get_current_user
    try:
        response=client.patch(
            f"/api/v1/applications/{application_id}/status",
            json={"status":"applied"},
        )
    finally:
        app.dependency_overrides[get_current_user]=owner_override
    data=response.json()

    assert response.status_code==404
    assert data["code"]=="application_not_found"
    get_response=client.get(f"/api/v1/applications/{application_id}")
    assert get_response.status_code==200
    assert get_response.json()["status"]=="saved"


def test_list_applications_hides_foreign_applications(
    client: TestClient,
    other_user: User,
) -> None:
    create_response=client.post(
        "/api/v1/applications/",
        json={
            'company_name':"openAI",
            "role_title":"Backend Enginerr",
        },
    )

    assert create_response.status_code==200
    owner_override=app.dependency_overrides[get_current_user]

    async def override_get_current_user()->User:
        return other_user
    app.dependency_overrides[get_current_user]=override_get_current_user
    try:
        response = client.get("/api/v1/applications/")
    finally:
        app.dependency_overrides[get_current_user] = owner_override

    assert response.status_code == 200
    assert response.json() == []
