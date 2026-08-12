from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tal.db.base import Base
from tal.features.auth.entities import User
from tal.features.resumes.entities import Resume, ResumeTextBlock
from tal.features.resumes.errors import ResumeExtractionError
from tal.features.resumes.extraction import ExtractedBlock, ExtractedDocument
from tal.features.resumes.models import ResumeStatus
from tal.features.resumes.processing import process_resume, save_extracted_document

FIXTURE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "resumes"


class FakeDownloadStorage:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.downloaded_keys: list[str] = []

    async def download(
        self,
        *,
        storage_key: str,
    ) -> bytes:
        self.downloaded_keys.append(storage_key)
        return self.data


@pytest.fixture
async def session()->AsyncIterator[AsyncSession]:
    engine=create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    SessionFactory=async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    async with SessionFactory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_save_extracted_document_preserves_block_provenance(
    session:AsyncSession, 
)->None:
    user=User(email="resume-processing@example.com")
    session.add(user)
    await session.flush()

    resume=Resume(
        user_id=user.id,
        original_filename="resume.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/resume.pdf",
        sha256="a"*64,
    )
    session.add(resume)
    await session.flush()

    document=ExtractedDocument(
        full_text="First page\n\nSecond page",
        blocks=(
            ExtractedBlock(
                text="First page",
                page_number=1,
            ),
            ExtractedBlock(
                text="Second page",
                page_number=2,
            ),
        ),
    )
    await save_extracted_document(
        resume_id=resume.id,
        document=document,
        session=session,
    )

    result=await session.execute(
        select(ResumeTextBlock)
        .where(ResumeTextBlock.resume_id == resume.id)
        .order_by(ResumeTextBlock.ordinal)
    )
    saved_blocks=result.scalars().all()
    assert [block.ordinal for block in saved_blocks] == [1, 2]
    assert [block.text for block in saved_blocks] == [
        "First page",
        "Second page",
    ]
    assert [block.page_number for block in saved_blocks] == [1, 2]
    assert [block.paragraph_number for block in saved_blocks] == [
        None,
        None,
    ]




async def test_process_resume_downloads_extracts_and_marks_ready(
        session:AsyncSession,
)->None:
    pdf_bytes=(
         FIXTURE_DIR / "two_page_resume.pdf"
    ).read_bytes()
    storage=FakeDownloadStorage(pdf_bytes)
    user=User(email="processing-owner@example.com")
    session.add(user)
    await session.flush()

    resume=Resume(
        user_id=user.id,
         original_filename="resume.pdf",
        content_type="application/pdf",
        size_bytes=len(pdf_bytes),
        storage_key="users/test/resumes/processing.pdf",
         sha256="b" * 64,
    )
    session.add(resume)
    await session.flush()

    await process_resume(
        resume_id=resume.id,
        session=session,
        storage=storage,
    )
    await session.refresh(resume)

    result=await session.execute(
        select(ResumeTextBlock)
        .where(ResumeTextBlock.resume_id==resume.id)
        .order_by(ResumeTextBlock.ordinal)
    )
    saved_blocks=result.scalars().all()

    assert storage.downloaded_keys==[resume.storage_key]
    assert resume.status==ResumeStatus.READY
    assert len(saved_blocks)==2
    assert [block.page_number for block in saved_blocks] == [1, 2]
    assert "Built FastAPI services" in saved_blocks[0].text
    assert "Python and PostgreSQL" in saved_blocks[1].text



@pytest.mark.asyncio
async def test_process_resume_marks_failed_when_extraction_fails(
    session: AsyncSession,
) -> None:
    corrupted_pdf = b"%PDF-1.7\ncorrupted\n%%EOF"
    storage = FakeDownloadStorage(corrupted_pdf)

    user = User(email="failed-processing@example.com")
    session.add(user)
    await session.flush()

    resume = Resume(
        user_id=user.id,
        original_filename="broken.pdf",
        content_type="application/pdf",
        size_bytes=len(corrupted_pdf),
        storage_key="users/test/resumes/broken.pdf",
        sha256="c" * 64,
    )
    session.add(resume)
    await session.flush()

    with pytest.raises(ResumeExtractionError):
        await process_resume(
            resume_id=resume.id,
            session=session,
            storage=storage,
        )

    await session.refresh(resume)

    result = await session.execute(
        select(ResumeTextBlock).where(
            ResumeTextBlock.resume_id == resume.id
        )
    )
    saved_blocks = result.scalars().all()

    assert resume.status == ResumeStatus.FAILED
    assert saved_blocks == []


@pytest.mark.asyncio
async def test_process_resume_is_idempotent_when_already_ready(
    session: AsyncSession,
) -> None:
    pdf_bytes = (
        FIXTURE_DIR / "two_page_resume.pdf"
    ).read_bytes()
    storage = FakeDownloadStorage(pdf_bytes)

    user = User(email="retry-processing@example.com")
    session.add(user)
    await session.flush()

    resume = Resume(
        user_id=user.id,
        original_filename="resume.pdf",
        content_type="application/pdf",
        size_bytes=len(pdf_bytes),
        storage_key="users/test/resumes/retry.pdf",
        sha256="d" * 64,
    )
    session.add(resume)
    await session.flush()

    await process_resume(
        resume_id=resume.id,
        session=session,
        storage=storage,
    )
    await process_resume(
        resume_id=resume.id,
        session=session,
        storage=storage,
    )

    await session.refresh(resume)

    result = await session.execute(
        select(ResumeTextBlock).where(
            ResumeTextBlock.resume_id == resume.id
        )
    )
    saved_blocks = result.scalars().all()

    assert resume.status == ResumeStatus.READY
    assert len(saved_blocks) == 2
    assert storage.downloaded_keys == [resume.storage_key]
