from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tal.db.base import Base
from tal.db.session import get_db_session
from tal.features.auth.dependencies import get_current_user
from tal.features.auth.entities import User
from tal.features.resumes.entities import Resume  # Registers table metadata
from tal.features.resumes.storage import get_resume_storage
from tal.main import app


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []

    async def upload(
        self,
        *,
        storage_key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        self.uploads.append(
            {
                "storage_key": storage_key,
                "data": data,
                "content_type": content_type,
            }
        )


@pytest.fixture
def fake_storage() -> FakeStorage:
    return FakeStorage()



test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestSessionFactory=async_sessionmaker(
    test_engine,
      expire_on_commit=False,)


@pytest.fixture
async def client(
    fake_storage: FakeStorage,
) -> AsyncIterator[TestClient]:
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async  with TestSessionFactory() as session:
        current_user=User(email="resume-owner@example.com")
        session.add(current_user)
        await session.commit()
        await session.refresh(current_user)

    async def override_get_db_session()->AsyncIterator[AsyncSession]:
        async with TestSessionFactory() as session:
            yield session

    async def override_get_current_user()->User:
        return current_user

    def override_get_resume_storage() -> FakeStorage:
        return fake_storage

    app.dependency_overrides[get_db_session]=override_get_db_session
    app.dependency_overrides[get_current_user]=override_get_current_user
    app.dependency_overrides[get_resume_storage] = override_get_resume_storage
    yield TestClient(app)
    app.dependency_overrides.clear()
    await test_engine.dispose()


def test_upload_pdf_creates_resume(
    client: TestClient,
    fake_storage: FakeStorage,
) -> None:
    pdf_bytes = b"%PDF-1.4\nsample resume content"

    response = client.post(
        "/api/v1/resumes/",
        files={
            "file": (
                "resume.pdf",
                pdf_bytes,
                "application/pdf",
            )
        },
    )
    data = response.json()

    assert response.status_code == 201
    assert data["original_filename"] == "resume.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["size_bytes"] == len(pdf_bytes)
    assert data["status"] == "uploaded"
    assert data["id"]
    assert data["created_at"]
    assert data["updated_at"]

    assert "storage_key" not in data
    assert "sha256" not in data

    assert len(fake_storage.uploads) == 1

    uploaded = fake_storage.uploads[0]
    assert uploaded["data"] == pdf_bytes
    assert uploaded["content_type"] == "application/pdf"

    storage_key = uploaded["storage_key"]
    assert storage_key.startswith("users/")
    assert "/resumes/" in storage_key
    assert storage_key.endswith(".pdf")
