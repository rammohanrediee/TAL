from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tal.db.session import get_db_session
from tal.features.applications.schemas import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationStatusUpdate,
)
from tal.features.applications.service import create_application as create_application_service
from tal.features.applications.service import get_application, update_application_status
from tal.features.applications.service import list_applications as list_application_service

router = APIRouter(prefix="/applications")


@router.post("/", response_model=ApplicationRead)
async def create_application(
    payload: ApplicationCreate, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> ApplicationRead:
    return await create_application_service(payload, session)


@router.get("/", response_model=list[ApplicationRead])
async def list_applications(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ApplicationRead]:
    return await list_application_service(session)


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_applications_id(
    application_id: UUID, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> ApplicationRead:
    return await get_application(application_id, session)


@router.patch("/{id}/status", response_model=ApplicationRead)
async def patch_application_status(
    id: UUID,
    payload: ApplicationStatusUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApplicationRead:
    return await update_application_status(id, payload, session)
