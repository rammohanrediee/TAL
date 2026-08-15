import re
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tal.features.resumes.entities import Resume, ResumeEvidence, ResumeTextBlock
from tal.features.resumes.errors import (
    EvidenceProvenanceError,
    ResumeNotFoundError,
    ResumeTextNotFoundError,
)
from tal.features.resumes.models import EvidenceType
from tal.features.resumes.schemas import EvidenceSourceBlock, ExtractedEvidenceCandidate
from tal.features.skills.normalization import SkillNormalizer
from tal.features.skills.taxonomy import SKILLS_V1_NORMALIZER


class EvidenceExtractor(Protocol):
    async def extract(
        self,
        *,
        blocks: tuple[EvidenceSourceBlock, ...],
    ) -> tuple[ExtractedEvidenceCandidate, ...]: ...


def _normalized_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _contains_normalized_phrase(
    *,
    phrase: str,
    text: str,
) -> bool:
    normalized_phrase = _normalized_text(phrase)
    normalized_text = _normalized_text(text)

    pattern = rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)"
    return re.search(pattern, normalized_text) is not None


def validate_evidence_provenance(
    *,
    evidence_type: EvidenceType,
    claim_text: str,
    source_quote: str,
    source_block: ResumeTextBlock | None,
) -> ResumeTextBlock:
    if source_block is None or source_quote not in source_block.text:
        raise EvidenceProvenanceError()

    if evidence_type is EvidenceType.SKILL and not _contains_normalized_phrase(
        phrase=claim_text,
        text=source_quote,
    ):
        raise EvidenceProvenanceError()

    return source_block


async def validate_candidate_provenance(
    *,
    resume_id: UUID,
    candidate: ExtractedEvidenceCandidate,
    session: AsyncSession,
) -> ResumeTextBlock:

    result = await session.execute(
        select(ResumeTextBlock).where(
            ResumeTextBlock.id == candidate.source_block_id,
            ResumeTextBlock.resume_id == resume_id,
        )
    )
    source_block = result.scalar_one_or_none()

    return validate_evidence_provenance(
        evidence_type=candidate.evidence_type,
        claim_text=candidate.claim_text,
        source_quote=candidate.source_quote,
        source_block=source_block,
    )


async def extract_resume_evidence(
    *,
    resume_id: UUID,
    extractor: EvidenceExtractor,
    skill_normalizer: SkillNormalizer = SKILLS_V1_NORMALIZER,
    session: AsyncSession,
) -> tuple[ResumeEvidence, ...]:
    resume_result = await session.execute(
        select(Resume).where(Resume.id == resume_id).with_for_update()
    )
    resume = resume_result.scalar_one_or_none()

    if resume is None:
        raise ResumeNotFoundError()

    existing_result = await session.execute(
        select(ResumeEvidence)
        .where(ResumeEvidence.resume_id == resume_id)
        .order_by(ResumeEvidence.created_at, ResumeEvidence.id)
    )
    existing_evidence = tuple(existing_result.scalars().all())

    if existing_evidence:
        return existing_evidence

    result = await session.execute(
        select(ResumeTextBlock)
        .where(ResumeTextBlock.resume_id == resume_id)
        .order_by(ResumeTextBlock.ordinal)
    )
    source_blocks = tuple(result.scalars().all())

    if not source_blocks:
        raise ResumeTextNotFoundError()

    source_blocks_by_id = {block.id: block for block in source_blocks}

    extractor_blocks = tuple(
        EvidenceSourceBlock(
            id=block.id,
            text=block.text,
            page_number=block.page_number,
            paragraph_number=block.paragraph_number,
        )
        for block in source_blocks
    )

    candidates = await extractor.extract(
        blocks=extractor_blocks,
    )

    for candidate in candidates:
        validate_evidence_provenance(
            evidence_type=candidate.evidence_type,
            claim_text=candidate.claim_text,
            source_quote=candidate.source_quote,
            source_block=source_blocks_by_id.get(candidate.source_block_id),
        )

    evidence_items: list[ResumeEvidence] = []

    for candidate in candidates:
        normalized_skill = (
            skill_normalizer.normalize(candidate.claim_text)
            if candidate.evidence_type is EvidenceType.SKILL
            else None
        )
        evidence_items.append(
            ResumeEvidence(
                resume_id=resume_id,
                source_block_id=candidate.source_block_id,
                evidence_type=candidate.evidence_type,
                extracted_text=candidate.claim_text,
                canonical_skill_key=(
                    normalized_skill.canonical_key if normalized_skill is not None else None
                ),
                canonical_skill_name=(
                    normalized_skill.canonical_name if normalized_skill is not None else None
                ),
                skill_match_type=(
                    normalized_skill.match_type if normalized_skill is not None else None
                ),
                skill_taxonomy_version=(
                    normalized_skill.taxonomy_version if normalized_skill is not None else None
                ),
                source_text=candidate.source_quote,
                confidence=candidate.confidence,
            )
        )
    evidence = tuple(evidence_items)
    session.add_all(evidence)

    await session.flush()

    return evidence
