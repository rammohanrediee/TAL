from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tal.db.base import Base
from tal.features.auth.entities import User
from tal.features.resumes.entities import (
    Resume,
    ResumeEvidence,
    ResumeTextBlock,
)
from tal.features.resumes.errors import (
    EvidenceProvenanceError,
    EvidenceSourceMismatchError,
    ResumeTextNotFoundError,
)
from tal.features.resumes.evidence import (
    correct_resume_evidence,
    create_resume_evidence,
)
from tal.features.resumes.evidence_extraction import (
    extract_resume_evidence,
    validate_candidate_provenance,
)
from tal.features.resumes.models import EvidenceStatus, EvidenceType
from tal.features.resumes.schemas import EvidenceSourceBlock, ExtractedEvidenceCandidate
from tal.features.skills.models import SkillMatchType


class FakeEvidenceExtractor:
    def __init__(
        self,
        *candidates: ExtractedEvidenceCandidate,
    ) -> None:
        self.candidates = candidates
        self.received_blocks: tuple[EvidenceSourceBlock, ...] = ()
        self.call_count = 0

    async def extract(
        self,
        *,
        blocks: tuple[EvidenceSourceBlock, ...],
    ) -> tuple[ExtractedEvidenceCandidate, ...]:
        self.call_count += 1
        self.received_blocks = blocks
        return self.candidates


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


async def test_resume_evidence_preserves_claim_and_provenance(
    session: AsyncSession,
) -> None:
    # Arrange
    user = User(email="evidence-owner@example.com")
    session.add(user)
    await session.flush()

    resume = Resume(
        user_id=user.id,
        original_filename="resume.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/evidence.pdf",
        sha256="e" * 64,
    )
    session.add(resume)
    await session.flush()

    source_block = ResumeTextBlock(
        resume_id=resume.id,
        ordinal=1,
        text="Built REST APIs using Python and FastAPI",
        page_number=1,
        paragraph_number=None,
    )
    session.add(source_block)
    await session.flush()

    evidence = ResumeEvidence(
        resume_id=resume.id,
        source_block_id=source_block.id,
        evidence_type=EvidenceType.SKILL,
        status=EvidenceStatus.PENDING,
        extracted_text="Built REST APIs using Python and FastAPI",
        source_text="Built REST APIs using Python and FastAPI",
        confidence=0.95,
    )
    session.add(evidence)
    await session.commit()

    # Act
    result = await session.execute(
        select(ResumeEvidence).where(
            ResumeEvidence.id == evidence.id,
        )
    )
    saved_evidence = result.scalar_one()

    # Assert
    assert saved_evidence.resume_id == resume.id
    assert saved_evidence.source_block_id == source_block.id
    assert saved_evidence.evidence_type is EvidenceType.SKILL
    assert saved_evidence.status is EvidenceStatus.PENDING
    assert saved_evidence.confidence == pytest.approx(0.95)
    assert saved_evidence.extracted_text == ("Built REST APIs using Python and FastAPI")
    assert saved_evidence.source_text == ("Built REST APIs using Python and FastAPI")


async def test_create_evidence_rejects_block_from_another_resume(
    session: AsyncSession,
) -> None:
    # Arrange
    user = User(email="provenance-owner@example.com")
    session.add(user)
    await session.flush()

    first_resume = Resume(
        user_id=user.id,
        original_filename="first.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/first.pdf",
        sha256="f" * 64,
    )
    second_resume = Resume(
        user_id=user.id,
        original_filename="second.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/second.pdf",
        sha256="g" * 64,
    )
    session.add_all([first_resume, second_resume])
    await session.flush()

    first_resume_block = ResumeTextBlock(
        resume_id=first_resume.id,
        ordinal=1,
        text="Built APIs using FastAPI",
        page_number=1,
        paragraph_number=None,
    )
    session.add(first_resume_block)
    await session.flush()

    # Act and assert
    with pytest.raises(EvidenceSourceMismatchError):
        await create_resume_evidence(
            resume_id=second_resume.id,
            source_block_id=first_resume_block.id,
            evidence_type=EvidenceType.SKILL,
            extracted_text="FastAPI",
            source_quote="Built APIs using FastAPI",
            confidence=0.90,
            session=session,
        )

    result = await session.execute(select(ResumeEvidence))
    assert result.scalars().all() == []


async def test_correct_evidence_preserves_original_claim(
    session: AsyncSession,
) -> None:
    # Arrange
    user = User(email="correction-owner@example.com")
    session.add(user)
    await session.flush()

    resume = Resume(
        user_id=user.id,
        original_filename="resume.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/correction.pdf",
        sha256="c" * 64,
    )
    session.add(resume)
    await session.flush()

    block = ResumeTextBlock(
        resume_id=resume.id,
        ordinal=1,
        text="Worked as a Python beginner",
    )
    session.add(block)
    await session.flush()

    evidence = await create_resume_evidence(
        resume_id=resume.id,
        source_block_id=block.id,
        evidence_type=EvidenceType.SKILL,
        extracted_text="Python beginner",
        source_quote="Worked as a Python beginner",
        confidence=0.85,
        session=session,
    )
    assert evidence.canonical_skill_key is None
    assert evidence.canonical_skill_name is None
    assert evidence.skill_match_type is SkillMatchType.UNMATCHED
    assert evidence.skill_taxonomy_version == "skills-v1"
    # Act
    corrected = await correct_resume_evidence(
        evidence_id=evidence.id,
        user_id=user.id,
        corrected_text="Python backend development",
        session=session,
    )

    # Assert
    assert corrected.status is EvidenceStatus.CORRECTED
    assert corrected.extracted_text == "Python beginner"
    assert corrected.corrected_text == "Python backend development"
    assert corrected.source_text == "Worked as a Python beginner"


async def test_provenance_rejects_quote_missing_from_source_block(
    session: AsyncSession,
) -> None:
    # Arrange
    user = User(email="provenance-validation@example.com")
    session.add(user)
    await session.flush()

    resume = Resume(
        user_id=user.id,
        original_filename="resume.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/provenance.pdf",
        sha256="p" * 64,
    )
    session.add(resume)
    await session.flush()

    block = ResumeTextBlock(
        resume_id=resume.id,
        ordinal=1,
        text="Built REST APIs using Python and FastAPI",
        page_number=1,
    )
    session.add(block)
    await session.flush()

    candidate = ExtractedEvidenceCandidate(
        evidence_type=EvidenceType.SKILL,
        claim_text="Kubernetes",
        source_block_id=block.id,
        source_quote="Led a Kubernetes migration",
        confidence=0.95,
    )

    # Act and assert
    with pytest.raises(EvidenceProvenanceError):
        await validate_candidate_provenance(
            resume_id=resume.id,
            candidate=candidate,
            session=session,
        )


async def test_provenance_rejects_skill_missing_from_valid_quote(
    session: AsyncSession,
) -> None:
    # Arrange
    user = User(email="unsupported-skill@example.com")
    session.add(user)
    await session.flush()

    resume = Resume(
        user_id=user.id,
        original_filename="resume.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/unsupported-skill.pdf",
        sha256="u" * 64,
    )
    session.add(resume)
    await session.flush()

    block = ResumeTextBlock(
        resume_id=resume.id,
        ordinal=1,
        text="Built APIs using Google Cloud",
        page_number=1,
    )
    session.add(block)
    await session.flush()

    candidate = ExtractedEvidenceCandidate(
        evidence_type=EvidenceType.SKILL,
        claim_text="Go",
        source_block_id=block.id,
        source_quote="Built APIs using Google Cloud",
        confidence=0.95,
    )

    # Act and assert
    with pytest.raises(EvidenceProvenanceError):
        await validate_candidate_provenance(
            resume_id=resume.id,
            candidate=candidate,
            session=session,
        )


async def test_extract_resume_evidence_persists_valid_candidate(
    session: AsyncSession,
) -> None:
    # Arrange
    user = User(email="extractor-owner@example.com")
    session.add(user)
    await session.flush()

    resume = Resume(
        user_id=user.id,
        original_filename="resume.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/extractor.pdf",
        sha256="x" * 64,
    )
    session.add(resume)
    await session.flush()

    block = ResumeTextBlock(
        resume_id=resume.id,
        ordinal=1,
        text="Built REST APIs using Python and FastAPI",
        page_number=1,
    )
    session.add(block)
    await session.flush()

    candidate = ExtractedEvidenceCandidate(
        evidence_type=EvidenceType.SKILL,
        claim_text="FastAPI",
        source_block_id=block.id,
        source_quote="Python and FastAPI",
        confidence=0.95,
    )
    extractor = FakeEvidenceExtractor(candidate)

    # Act
    evidence = await extract_resume_evidence(
        resume_id=resume.id,
        extractor=extractor,
        session=session,
    )

    # Assert
    assert len(extractor.received_blocks) == 1
    assert extractor.received_blocks[0].id == block.id
    assert extractor.received_blocks[0].text == block.text

    assert len(evidence) == 1
    assert evidence[0].status is EvidenceStatus.PENDING
    assert evidence[0].extracted_text == "FastAPI"
    assert evidence[0].source_text == "Python and FastAPI"
    assert evidence[0].confidence == pytest.approx(0.95)
    assert evidence[0].canonical_skill_key == "fastapi"
    assert evidence[0].canonical_skill_name == "FastAPI"
    assert evidence[0].skill_match_type is SkillMatchType.EXACT
    assert evidence[0].skill_taxonomy_version == "skills-v1"

    # Act again to simulate a retried background job.
    repeated_evidence = await extract_resume_evidence(
        resume_id=resume.id,
        extractor=extractor,
        session=session,
    )

    # Assert the retry reuses the first extraction.
    assert extractor.call_count == 1
    assert [item.id for item in repeated_evidence] == [item.id for item in evidence]


async def test_extract_resume_evidence_rejects_resume_without_blocks(
    session: AsyncSession,
) -> None:
    # Arrange
    user = User(email="empty-evidence@example.com")
    session.add(user)
    await session.flush()

    resume = Resume(
        user_id=user.id,
        original_filename="empty.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/empty-evidence.pdf",
        sha256="z" * 64,
    )
    session.add(resume)
    await session.flush()

    extractor = FakeEvidenceExtractor()

    # Act and assert
    with pytest.raises(ResumeTextNotFoundError):
        await extract_resume_evidence(
            resume_id=resume.id,
            extractor=extractor,
            session=session,
        )

    assert extractor.call_count == 0


async def test_create_non_skill_evidence_leaves_skill_fields_empty(
    session: AsyncSession,
) -> None:
    # Arrange
    user = User(email="experience-evidence@example.com")
    session.add(user)
    await session.flush()

    resume = Resume(
        user_id=user.id,
        original_filename="experience.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/experience-evidence.pdf",
        sha256="n" * 64,
    )
    session.add(resume)
    await session.flush()

    block = ResumeTextBlock(
        resume_id=resume.id,
        ordinal=1,
        text="Led a backend engineering team",
    )
    session.add(block)
    await session.flush()

    # Act
    evidence = await create_resume_evidence(
        resume_id=resume.id,
        source_block_id=block.id,
        evidence_type=EvidenceType.EXPERIENCE,
        extracted_text="Led a backend engineering team",
        source_quote="Led a backend engineering team",
        confidence=0.90,
        session=session,
    )

    # Assert
    assert evidence.canonical_skill_key is None
    assert evidence.canonical_skill_name is None
    assert evidence.skill_match_type is None
    assert evidence.skill_taxonomy_version is None


async def test_create_evidence_rejects_skill_unsupported_by_quote(
    session: AsyncSession,
) -> None:
    # Arrange
    user = User(email="manual-provenance@example.com")
    session.add(user)
    await session.flush()

    resume = Resume(
        user_id=user.id,
        original_filename="manual.pdf",
        content_type="application/pdf",
        size_bytes=100,
        storage_key="users/test/resumes/manual-provenance.pdf",
        sha256="m" * 64,
    )
    session.add(resume)
    await session.flush()

    block = ResumeTextBlock(
        resume_id=resume.id,
        ordinal=1,
        text="Built APIs using Python",
    )
    session.add(block)
    await session.flush()

    # Act and assert
    with pytest.raises(EvidenceProvenanceError):
        await create_resume_evidence(
            resume_id=resume.id,
            source_block_id=block.id,
            evidence_type=EvidenceType.SKILL,
            extracted_text="Kubernetes",
            source_quote="Built APIs using Python",
            confidence=0.90,
            session=session,
        )

    result = await session.execute(select(ResumeEvidence))
    assert result.scalars().all() == []
