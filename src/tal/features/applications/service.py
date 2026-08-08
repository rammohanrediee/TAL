from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tal.features.applications.entities import Application
from tal.features.applications.errors import ApplicationNotFoundError
from tal.features.applications.schemas import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationStatusUpdate,
)


async def create_application(payload: ApplicationCreate, session: AsyncSession, user_id: UUID) -> ApplicationRead:
    data = payload.model_dump()
    data["job_url"] = str(payload.job_url) if payload.job_url else None
    data["user_id"] = user_id
    application = Application(**data)
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return ApplicationRead.model_validate(application)


async def list_applications(session: AsyncSession,user_id: UUID) -> list[ApplicationRead]:
    result = await session.execute(select(Application).where(Application.user_id == user_id))
    applications = result.scalars().all()
    return [ApplicationRead.model_validate(application) for application in applications]


async def get_application(
    application_id: UUID,
    session: AsyncSession,
    user_id: UUID
) -> ApplicationRead:
    result = await session.execute(
        select(Application).where(Application.id == application_id, Application.user_id == user_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise ApplicationNotFoundError(application_id)
    return ApplicationRead.model_validate(application)


async def update_application_status(
    id: UUID,
    payload: ApplicationStatusUpdate,
    session: AsyncSession,
    user_id: UUID
) -> ApplicationRead:
    result= await session.execute(
        select(Application).where(Application.id == id, Application.user_id == user_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise ApplicationNotFoundError(id)
    application.status = payload.status
    await session.commit()
    await session.refresh(application)
    return ApplicationRead.model_validate(application)
