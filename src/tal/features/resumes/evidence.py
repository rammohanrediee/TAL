from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tal.features.resumes.entities import Resume, ResumeEvidence, ResumeTextBlock
from tal.features.resumes.errors import (
    EvidenceNotFoundError,
    EvidenceSourceMismatchError,
    ResumeNotFoundError,
)
from tal.features.resumes.evidence_extraction import validate_evidence_provenance
from tal.features.resumes.models import EvidenceStatus, EvidenceType
from tal.features.skills.normalization import SkillNormalizer
from tal.features.skills.taxonomy import SKILLS_V1_NORMALIZER


async def create_resume_evidence(
    *,
    resume_id: UUID,
    source_block_id: UUID,
    evidence_type: EvidenceType,
    extracted_text: str,
    confidence: float,
    session: AsyncSession,
    skill_normalizer: SkillNormalizer = SKILLS_V1_NORMALIZER,
    source_quote: str,
) -> ResumeEvidence:
    result = await session.execute(
        select(ResumeTextBlock).where(
            ResumeTextBlock.resume_id == resume_id,
            ResumeTextBlock.id == source_block_id,
        )
    )
    source_block = result.scalar_one_or_none()

    if source_block is None:
        raise EvidenceSourceMismatchError()

    validate_evidence_provenance(
        evidence_type=evidence_type,
        claim_text=extracted_text,
        source_quote=source_quote,
        source_block=source_block,
    )

    normalized_skill = (
        skill_normalizer.normalize(extracted_text)
        if evidence_type is EvidenceType.SKILL
        else None
    )

    evidence = ResumeEvidence(
        resume_id=resume_id,
        source_block_id=source_block.id,
        evidence_type=evidence_type,
        extracted_text=extracted_text,
        canonical_skill_key=(
            normalized_skill.canonical_key if normalized_skill is not None else None
        ),
        canonical_skill_name=(
            normalized_skill.canonical_name if normalized_skill is not None else None
        ),
        skill_match_type=(normalized_skill.match_type if normalized_skill is not None else None),
        skill_taxonomy_version=(
            normalized_skill.taxonomy_version if normalized_skill is not None else None
        ),
        source_text=source_quote,
        confidence=confidence,
    )

    session.add(evidence)
    await session.flush()

    return evidence


async def correct_resume_evidence(
    *,
    evidence_id: UUID,
    user_id: UUID,
    corrected_text: str,
    session: AsyncSession,
) -> ResumeEvidence:

    result = await session.execute(
        select(ResumeEvidence)
        .join(
            Resume,
            Resume.id == ResumeEvidence.resume_id,
        )
        .where(ResumeEvidence.id == evidence_id, Resume.user_id == user_id)
    )
    evidence = result.scalar_one_or_none()

    if evidence is None:
        raise EvidenceNotFoundError()

    cleaned_text = corrected_text.strip()
    evidence.corrected_text = cleaned_text
    evidence.status = EvidenceStatus.CORRECTED

    await session.flush()
    return evidence


async def list_resume_evidence(
    *,
    resume_id: UUID,
    user_id: UUID,
    session: AsyncSession,
) -> tuple[ResumeEvidence, ...]:
    resume_result = await session.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
        )
    )
    resume = resume_result.scalar_one_or_none()
    if resume is None:
        raise ResumeNotFoundError()

    evidence = await session.execute(
        select(ResumeEvidence)
        .where(ResumeEvidence.resume_id == resume_id)
        .order_by(
            ResumeEvidence.created_at,
            ResumeEvidence.id,
        )
    )
    return tuple(evidence.scalars().all())
