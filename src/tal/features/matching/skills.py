from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tal.features.conversations.entities import Conversation
from tal.features.resumes.entities import Resume, ResumeEvidence
from tal.features.resumes.models import EvidenceStatus, EvidenceType, ResumeStatus


async def resolve_resume_id(
    session: AsyncSession,
    user_id: UUID,
    *,
    conversation_id: UUID | None = None,
) -> UUID | None:
    if conversation_id is not None:
        conversation = await session.get(Conversation, conversation_id)
        if (
            conversation is not None
            and conversation.user_id == user_id
            and conversation.resume_id is not None
        ):
            return conversation.resume_id

    result = await session.execute(
        select(Resume.id)
        .where(Resume.user_id == user_id, Resume.status == ResumeStatus.READY)
        .order_by(Resume.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def load_user_skill_labels(
    session: AsyncSession,
    user_id: UUID,
    *,
    resume_id: UUID | None,
) -> tuple[str, ...]:
    if resume_id is None:
        return ()

    resume = await session.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    if resume is None:
        return ()

    result = await session.execute(
        select(ResumeEvidence).where(
            ResumeEvidence.resume_id == resume_id,
            ResumeEvidence.evidence_type == EvidenceType.SKILL,
            ResumeEvidence.status.in_((EvidenceStatus.CONFIRMED, EvidenceStatus.CORRECTED)),
        )
    )
    labels: list[str] = []
    seen: set[str] = set()
    for item in result.scalars():
        label = (
            item.canonical_skill_name or item.corrected_text or item.extracted_text
        ).strip()
        if not label:
            continue
        key = label.casefold()
        if key in seen:
            continue
        seen.add(key)
        labels.append(label)
    return tuple(labels)