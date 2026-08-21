
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from tal.db.session import get_db_session
from tal.features.auth.dependencies import get_current_user
from tal.features.auth.entities import User
from tal.features.resumes.evidence import (
    correct_resume_evidence,
    list_resume_evidence,
)
from tal.features.resumes.evidence_client_factory import (
    create_configured_evidence_extractor,
)
from tal.features.resumes.processing import process_resume
from tal.features.resumes.schemas import ResumeEvidenceCorrection, ResumeEvidenceRead, ResumeRead
from tal.features.resumes.service import (
    create_resume_from_upload,
    delete_resume,
    get_resume_by_id,
)
from tal.features.resumes.storage import StorageBackend, get_resume_storage
from tal.worker.tasks import resumes as resume_tasks

router = APIRouter(prefix="/resumes")

logger = logging.getLogger(__name__)


@router.post("/", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
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
    try:
        resume_tasks.process_resume_task.delay(str(resume.id))
    except Exception:
        logger.exception(
            "Task broker unavailable; processing résumé %s inline",
            resume.id,
        )

        try:
            await process_resume(
                resume_id=resume.id,
                session=session,
                storage=storage,
                evidence_extractor=create_configured_evidence_extractor(),
            )
        except Exception:
            logger.exception(
                "Inline processing failed for résumé %s",
                resume.id,
            )

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

@router.get("/{resume_id}/evidence",response_model=list[ResumeEvidenceRead])
async def get_resume_evidence(
    resume_id:UUID,
    current_user:Annotated[User, Depends(get_current_user)],
    session:Annotated[AsyncSession, Depends(get_db_session)],
)->list[ResumeEvidenceRead]:
    return await list_resume_evidence(
        resume_id=resume_id,
        user_id=current_user.id,
        session=session,
    )


@router.patch("/evidence/{evidence_id}",
              response_model=ResumeEvidenceRead)
async def correct_evidence(
    evidence_id:UUID,
    correction:ResumeEvidenceCorrection,
    current_user:Annotated[User, Depends(get_current_user)],
    session:Annotated[AsyncSession, Depends(get_db_session)],
)->ResumeEvidenceRead:
    evidence=await correct_resume_evidence(
        evidence_id=evidence_id,
        user_id=current_user.id,
        corrected_text=correction.corrected_text,
        session=session
    )
    await session.commit()
    await session.refresh(evidence)

    return evidence
