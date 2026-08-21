from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from tal.features.resumes.entities import Resume, ResumeTextBlock
from tal.features.resumes.errors import (
    ResumeExtractionError,
    ResumeNotFoundError,
)
from tal.features.resumes.evidence_extraction import (
    EvidenceExtractor,
    extract_resume_evidence,
)
from tal.features.resumes.extraction import (
    ExtractedDocument,
    extract_docx,
    extract_pdf,
)
from tal.features.resumes.models import ResumeStatus
from tal.features.resumes.storage import StorageBackend

PDF_CONTENT_TYPE = "application/pdf"

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


async def save_extracted_document(
        *,
        resume_id:UUID,
        document:ExtractedDocument,
        session:AsyncSession
)->None:
    saved_blocks=[
        ResumeTextBlock(
            resume_id=resume_id,
            ordinal=ordinal,
            text=block.text,
            page_number=block.page_number,
            paragraph_number=block. paragraph_number,
        )
        for ordinal,block in enumerate(
            document.blocks,
            start=1
        )
    ]
    session.add_all(saved_blocks)
    await session.flush()

async def process_resume(
        *,
        resume_id:UUID,
        session:AsyncSession,
        storage:StorageBackend,
        evidence_extractor:EvidenceExtractor,
)->None:
    resume=await session.get(Resume,resume_id)

    if resume is None:
        raise ResumeNotFoundError()

    if resume.status==ResumeStatus.READY:
        return 

    storage_key=resume.storage_key
    content_type=resume.content_type

    resume.status=ResumeStatus.PROCESSING
    await session.commit()
    try:

        data=await storage.download(
            storage_key=storage_key,
        )
        if content_type==PDF_CONTENT_TYPE:
            document=extract_pdf(data)
        elif content_type==DOCX_CONTENT_TYPE:
            document=extract_docx(data)

        else:
            raise ResumeExtractionError()

    except ResumeExtractionError:
        resume.status = ResumeStatus.FAILED
        await session.commit()
        raise

    await save_extracted_document(
        resume_id=resume.id,
        document=document,
        session=session,
    )
    await extract_resume_evidence(
        resume_id=resume.id,
        extractor=evidence_extractor,
        session=session,
    )
    resume.status=ResumeStatus.READY
    await session.commit()