
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from tal.db.session import get_db_session
from tal.features.resumes.schemas import ResumeRead
from tal.features.auth.dependencies import get_current_user
from tal.features.auth.entities import User
from tal.features.resumes.service import create_resume_from_upload
from tal.features.resumes.storage import StorageBackend, get_resume_storage


router=APIRouter(prefix="/resumes")

@router.post("/", response_model=ResumeRead,
             status_code=status.HTTP_201_CREATED,)
async def upload_resume(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[StorageBackend, Depends(get_resume_storage)],
    file: Annotated[UploadFile,File()])-> ResumeRead:
    return await create_resume_from_upload(file, session, current_user.id, storage)
