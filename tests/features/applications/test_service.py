import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tal.db.base import Base
from tal.features.applications.entities import Application
from tal.features.applications.models import ApplicationStatus
from tal.features.applications.schemas import ApplicationCreate
from tal.features.applications.service import create_application


@pytest.mark.asyncio
async def test_create_application_persists_application() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            payload = ApplicationCreate(
                company_name="OpenAI",
                role_title="Backend Engineer",
                job_url="https://openai.com",
            )

            result = await create_application(payload, session)
            stored_application = await session.get(Application, result.id)

            assert result.company_name == "OpenAI"
            assert result.role_title == "Backend Engineer"
            assert result.status is ApplicationStatus.SAVED
            assert result.id is not None
            assert result.created_at is not None
            assert result.updated_at is not None

            assert stored_application is not None
            assert stored_application.id == result.id
            assert stored_application.status is ApplicationStatus.SAVED
    finally:
        await engine.dispose()
