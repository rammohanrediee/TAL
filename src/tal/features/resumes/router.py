
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from tal.db.session import get_db_session
from tal.features.auth.dependencies import get_current_user
from tal.features.auth.entities import User
from tal.features.resumes.schemas import ResumeRead
from tal.features.resumes.service import (
    create_resume_from_upload,
    delete_resume,
    get_resume_by_id,
)
from tal.features.resumes.storage import StorageBackend, get_resume_storage
from tal.worker.tasks import resumes as resume_tasks

router=APIRouter(prefix="/resumes")

@router.post("/", response_model=ResumeRead,
             status_code=status.HTTP_201_CREATED,)

async def upload_resume(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[StorageBackend, Depends(get_resume_storage)],
    file: Annotated[UploadFile, File()],
) -> ResumeRead:
    resume = await create_resume_from_upload(
        file,
        session,
        current_user.id,
        storage,
    )

    resume_tasks.process_resume_task.delay(str(resume.id))

    return resume


@router.get(
    "/{resume_id}",response_model=ResumeRead
)
async def get_resume(
    resume_id:UUID,
     session: Annotated[AsyncSession, Depends(get_db_session)],
     current_user: Annotated[User, Depends(get_current_user)],
)->ResumeRead:
    return await get_resume_by_id(resume_id,current_user.id,session)



@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def del_resume(
    resume_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[StorageBackend, Depends(get_resume_storage)],
) -> None:
    await delete_resume(
        resume_id=resume_id,
        user_id=current_user.id,
        session=session,
        storage=storage,
    )
