from hashlib import sha256
from io import BytesIO
from uuid import UUID, uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tal.core.config import get_settings
from tal.features.resumes.entities import Resume
from tal.features.resumes.errors import (
    EmptyResumeError,
    InvalidResumeFilenameError,
    ResumeNotFoundError,
    ResumeTooLargeError,
    UnsupportedResumeTypeError,
)
from tal.features.resumes.schemas import ResumeRead
from tal.features.resumes.storage import StorageBackend

PDF_CONTENT_TYPE = "application/pdf"

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)



async def _read_upload(file:UploadFile)->bytes:
    settings=get_settings()
    max_bytes=settings.resume_max_upload_bytes
    data=await file.read(max_bytes+1)
    if not data:
        raise EmptyResumeError()
    if len(data)>max_bytes:
        raise ResumeTooLargeError(max_bytes)

    return data


def _detect_resume_type(data:bytes)->tuple[str,str]:
    if data.startswith(b"%PDF-"):
        return PDF_CONTENT_TYPE, ".pdf"
    try:
        with ZipFile(BytesIO(data)) as archive:
            filenames=set(archive.namelist())
    except(BadZipFile,OSError):
        raise UnsupportedResumeTypeError()

    required_docx_file={
          "[Content_Types].xml",
        "word/document.xml",
    }

    if required_docx_file.issubset(filenames):
        return DOCX_CONTENT_TYPE, ".docx"
    raise UnsupportedResumeTypeError()

def _safe_filename(filename:str|None)->str:
    if filename is None:
        raise InvalidResumeFilenameError()
    safe_filename=filename.replace("\\", "/").rsplit("/", 1)[-1]

    if not safe_filename or len(safe_filename)>255:
        raise InvalidResumeFilenameError()

    return safe_filename




async def create_resume_from_upload(
    file: UploadFile,
    session: AsyncSession,
    user_id: UUID,
    storage: StorageBackend,
) -> ResumeRead:
    data=await _read_upload(file)

    detected_content_type,extension=_detect_resume_type(data)
    original_filename=_safe_filename(file.filename)

    resume_id=uuid4()

    storage_key=(
        f"users/{user_id}/resumes/"
        f"{resume_id}{extension}"
    )
    if (not original_filename.lower().endswith(extension) or 
    file.content_type!=detected_content_type):
        raise UnsupportedResumeTypeError()

    resume=Resume(
        id=resume_id,
        user_id=user_id,
        original_filename=original_filename,
        content_type=detected_content_type,
        size_bytes=len(data),
        storage_key=storage_key,
        sha256=sha256(data).hexdigest(),
    )

    session.add(resume)

    try:
        await session.flush()

        await storage.upload(
            storage_key=storage_key,
            data=data,
            content_type=detected_content_type,
        )

        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(resume)

    return ResumeRead.model_validate(resume)


async def  delete_resume(
        resume_id:UUID,
        user_id:UUID,
        session:AsyncSession,
        storage:StorageBackend
)->None:
    result=await session.execute(
        select(Resume).where(
            Resume.user_id==user_id,
              Resume.id==resume_id)
            )
    resume=result.scalar_one_or_none()
    if resume is None:
        raise ResumeNotFoundError()

    await storage.delete(storage_key=resume.storage_key)
    await session.delete(resume)
    await session.commit()