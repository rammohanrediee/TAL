from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tal.features.matching.skills import load_user_skill_labels, resolve_resume_id
from tal.features.resumes.entities import Resume, ResumeEvidence
from tal.features.resumes.models import EvidenceStatus, EvidenceType


class ProfileSummary(BaseModel):
    resume_id: UUID | None
    resume_status: str | None
    skills: list[str]
    experience_highlights: list[str]


async def build_profile_summary(
    session: AsyncSession,
    user_id: UUID,
    *,
    conversation_id: UUID | None = None,
) -> ProfileSummary:
    resume_id = await resolve_resume_id(session, user_id, conversation_id=conversation_id)
    if resume_id is None:
        return ProfileSummary(
            resume_id=None,
            resume_status=None,
            skills=[],
            experience_highlights=[],
        )

    resume = await session.get(Resume, resume_id)
    skills = list(await load_user_skill_labels(session, user_id, resume_id=resume_id))

    result = await session.execute(
        select(ResumeEvidence)
        .where(
            ResumeEvidence.resume_id == resume_id,
            ResumeEvidence.evidence_type == EvidenceType.EXPERIENCE,
            ResumeEvidence.status.in_((EvidenceStatus.CONFIRMED, EvidenceStatus.CORRECTED)),
        )
        .order_by(ResumeEvidence.created_at)
        .limit(5)
    )
    highlights = [
        (item.corrected_text or item.extracted_text).strip()
        for item in result.scalars()
        if (item.corrected_text or item.extracted_text or "").strip()
    ]

    return ProfileSummary(
        resume_id=resume_id,
        resume_status=resume.status.value if resume else None,
        skills=skills,
        experience_highlights=highlights,
    )