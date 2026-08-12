from collections.abc import AsyncIterator
from io import BytesIO
from typing import Any
from zipfile import ZipFile

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
from tal.features.resumes.storage import get_resume_storage
from tal.main import app
from tal.worker.tasks import resumes as resume_tasks


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[dict[str, Any]] = []
        self.deletions:list[str]=[]

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
    async def delete(
            self,
            *,
            storage_key:str,
    )->None:
        self.deletions.append(storage_key)



@pytest.fixture
def fake_storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture(autouse=True)
def queued_resume_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> list[str]:
    resume_ids: list[str] = []

    def fake_delay(resume_id: str) -> None:
        resume_ids.append(resume_id)

    monkeypatch.setattr(
        resume_tasks.process_resume_task,
        "delay",
        fake_delay,
    )

    return resume_ids


test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestSessionFactory = async_sessionmaker(
    test_engine,
    expire_on_commit=False,
)


@pytest.fixture
async def client(
    fake_storage: FakeStorage,
) -> AsyncIterator[TestClient]:
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    async with TestSessionFactory() as session:
        current_user = User(email="resume-owner@example.com")
        session.add(current_user)
        await session.commit()
        await session.refresh(current_user)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with TestSessionFactory() as session:
            yield session

    async def override_get_current_user() -> User:
        return current_user

    def override_get_resume_storage() -> FakeStorage:
        return fake_storage

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_resume_storage] = override_get_resume_storage

    yield TestClient(app)

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.fixture
async def other_user(
    client: TestClient,
) -> User:
    async with TestSessionFactory() as session:
        user = User(email="other-resume-user@example.com")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user



def test_get_resume_hides_foreign_owned_resume(
        client:TestClient,
        other_user:User,
)->None:
    upload_response=client.post(
        "/api/v1/resumes/",
        files={
            "file":(
                 "resume.pdf",
                b"%PDF-1.4\nprivate resume content",
                "application/pdf",
            )
        },
    )
    assert upload_response.status_code==201
    resume_id=upload_response.json()["id"]

    owner_override=app.dependency_overrides[get_current_user]

    async def override_get_current_user()->User:
        return other_user

    app.dependency_overrides[
        get_current_user
    ]=override_get_current_user

    try:
        response=client.get(
            f"/api/v1/resumes/{resume_id}"
        )
    finally:
        app.dependency_overrides[
            get_current_user
        ]=owner_override

    data=response.json()

    assert response.status_code==404
    assert data["code"]=="resume_not_found"





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


def test_upload_docx_creates_resume(
    client: TestClient,
    fake_storage: FakeStorage,
) -> None:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")

    docx_bytes = buffer.getvalue()
    docx_content_type = (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    )

    response = client.post(
        "/api/v1/resumes/",
        files={
            "file": (
                "resume.docx",
                docx_bytes,
                docx_content_type,
            )
        },
    )
    data = response.json()

    assert response.status_code == 201
    assert data["original_filename"] == "resume.docx"
    assert data["content_type"] == docx_content_type
    assert data["size_bytes"] == len(docx_bytes)
    assert data["status"] == "uploaded"

    assert len(fake_storage.uploads) == 1

    uploaded = fake_storage.uploads[0]
    assert uploaded["data"] == docx_bytes
    assert uploaded["content_type"] == docx_content_type
    assert uploaded["storage_key"].endswith(".docx")


def test_upload_rejects_disguised_invalid_pdf(
    client: TestClient,
    fake_storage: FakeStorage,
) -> None:
    response = client.post(
        "/api/v1/resumes/",
        files={
            "file": (
                "fake.pdf",
                b"this is not a real PDF",
                "application/pdf",
            )
        },
    )
    data = response.json()

    assert response.status_code == 415
    assert data["code"] == "unsupported_resume_type"
    assert fake_storage.uploads == []


def test_upload_rejects_disguised_invalid_docx(
        client:TestClient,
        fake_storage:FakeStorage,
)->None:
    buffer=BytesIO()
    with ZipFile(buffer,"w") as archive:
        archive.writestr("[Content_Types].xml","<Types/>")
    docx_bytes=buffer.getvalue()
    docx_content_type=(
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    )

    response=client.post(
        "/api/v1/resumes/",
        files={
            "file":(
                "fake.docx",
                docx_bytes,
                docx_content_type,
            )
        },
    )
    data=response.json()

    assert response.status_code==415
    assert data["code"]=="unsupported_resume_type"
    assert fake_storage.uploads==[]


def test_upload_rejects_pdf_content_with_docx_filename(
    client: TestClient,
    fake_storage: FakeStorage,
) -> None:
    docx_content_type = (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    )

    response = client.post(
        "/api/v1/resumes/",
        files={
            "file": (
                "resume.docx",
                b"%PDF-1.4\nresume",
                docx_content_type,
            )
        },
    )
    data = response.json()

    assert response.status_code == 415
    assert data["code"] == "unsupported_resume_type"
    assert fake_storage.uploads == []


def test_delete_resume_removes_stored_object(
    client: TestClient,
    fake_storage: FakeStorage,
) -> None:
    upload_response = client.post(
        "/api/v1/resumes/",
        files={
            "file": (
                "resume.pdf",
                b"%PDF-1.4\nresume content",
                "application/pdf",
            )
        },
    )

    assert upload_response.status_code == 201

    resume_id = upload_response.json()["id"]
    storage_key = fake_storage.uploads[0]["storage_key"]

    delete_response = client.delete(
        f"/api/v1/resumes/{resume_id}"
    )

    assert delete_response.status_code == 204
    assert fake_storage.deletions == [storage_key]



def test_successful_upload_queues_resume_processing(
    client: TestClient,
    queued_resume_ids: list[str],
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
    assert queued_resume_ids == [data["id"]]


def test_get_resume_returns_status_for_owner(
    client: TestClient,
) -> None:
    upload_response = client.post(
        "/api/v1/resumes/",
        files={
            "file": (
                "resume.pdf",
                b"%PDF-1.4\nsample resume content",
                "application/pdf",
            )
        },
    )
    resume_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/resumes/{resume_id}"
    )
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == resume_id
    assert data["status"] == "uploaded"