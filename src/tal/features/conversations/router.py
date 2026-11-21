import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tal.core.config import get_settings, settings
from tal.core.errors import DomainError
from tal.db.session import get_db_session
from tal.features.auth.dependencies import get_current_user
from tal.features.auth.entities import User
from tal.features.conversations.entities import Conversation
from tal.features.conversations.schemas import ChatConnectionToken, ConversationRead
from tal.features.resumes.entities import ResumeEvidence, ResumeTextBlock
from tal.features.resumes.evidence_client_factory import create_configured_evidence_extractor
from tal.features.resumes.models import EvidenceStatus
from tal.features.resumes.processing import process_resume
from tal.features.resumes.service import (
    create_resume_from_upload,
    delete_resume,
)
from tal.features.resumes.storage import StorageBackend, get_resume_storage

router = APIRouter(prefix="/conversations")
logger = logging.getLogger(__name__)


async def resume_chat_context(resume_id: UUID, session: AsyncSession) -> tuple[str, bool]:
    evidence_result = await session.execute(
        select(ResumeEvidence)
        .where(
            ResumeEvidence.resume_id == resume_id,
            ResumeEvidence.status != EvidenceStatus.REJECTED,
        )
        .order_by(ResumeEvidence.created_at, ResumeEvidence.id)
    )
    evidence = evidence_result.scalars().all()
    blocks_result = await session.execute(
        select(ResumeTextBlock)
        .where(ResumeTextBlock.resume_id == resume_id)
        .order_by(ResumeTextBlock.ordinal)
    )
    blocks = blocks_result.scalars().all()
    claims = "\n".join(
        f"- {item.evidence_type.value}: {item.corrected_text or item.extracted_text} "
        f"(source: {item.source_text})" for item in evidence
    )
    source_lines = []
    for block in blocks:
        location = (
            f"page {block.page_number}"
            if block.page_number is not None
            else f"paragraph {block.paragraph_number}"
        )
        source_lines.append(f"[{location}] {block.text}")
    source = "\n".join(source_lines)
    context = f"Extracted evidence:\n{claims or '(none)'}\n\nRésumé source text:\n{source}"
    return context[:12_000], len(context) > 12_000


async def owned_conversation(
    conversation_id: UUID, user_id: UUID, session: AsyncSession
) -> Conversation:
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Conversation:
    conversation = Conversation(user_id=current_user.id)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[Conversation]:
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.deleted_at.is_(None))
        .order_by(Conversation.created_at.desc())
        .limit(100)
    )
    return list(result.scalars().all())


@router.post("/{conversation_id}/connection-token", response_model=ChatConnectionToken)
async def create_connection_token(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatConnectionToken:
    conversation = await owned_conversation(conversation_id, current_user.id, session)
    if conversation.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    expires_at = datetime.now(UTC) + timedelta(seconds=60)
    token = jwt.encode(
        {
            "sub": str(current_user.id),
            "cid": str(conversation.id),
            "aud": "tal-chat",
            "exp": expires_at,
            "iat": datetime.now(UTC),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    return ChatConnectionToken(token=token, expires_at=expires_at)


@router.post("/{conversation_id}/attachment", status_code=status.HTTP_201_CREATED)
async def attach_resume(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[StorageBackend, Depends(get_resume_storage)],
    file: Annotated[UploadFile, File()],
) -> dict[str, str | bool]:
    conversation = await owned_conversation(conversation_id, current_user.id, session)
    if conversation.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    resume = await create_resume_from_upload(file, session, current_user.id, storage)
    try:
        await process_resume(
            resume_id=resume.id,
            session=session,
            storage=storage,
        )
        if get_settings().evidence_provider != "none":
            try:
                await process_resume(
                    resume_id=resume.id,
                    session=session,
                    storage=storage,
                    evidence_extractor=create_configured_evidence_extractor(),
                )
            except Exception:
                await session.rollback()
                logger.exception("Optional evidence extraction failed for résumé %s", resume.id)
                conversation = await owned_conversation(conversation_id, current_user.id, session)
        text, truncated = await resume_chat_context(resume.id, session)
    except DomainError:
        await session.rollback()
        try:
            await delete_resume(resume.id, current_user.id, session, storage)
        except Exception:
            logger.exception("Could not remove failed résumé %s", resume.id)
        raise
    except Exception as error:
        await session.rollback()
        try:
            await delete_resume(resume.id, current_user.id, session, storage)
        except Exception:
            logger.exception("Could not remove failed résumé %s", resume.id)
        logger.exception("Résumé processing failed for chat %s", conversation_id)
        raise HTTPException(
            status_code=502, detail="Résumé processing failed. Try again."
        ) from error
    previous_resume_id = conversation.resume_id
    conversation.resume_id = resume.id
    await session.commit()
    if previous_resume_id is not None:
        try:
            await delete_resume(previous_resume_id, current_user.id, session, storage)
        except Exception:
            logger.exception("Could not remove replaced résumé %s", previous_resume_id)
    return {
        "filename": resume.original_filename,
        "resume_id": str(resume.id),
        "text": text,
        "truncated": truncated,
    }


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[StorageBackend, Depends(get_resume_storage)],
) -> None:
    conversation = await owned_conversation(conversation_id, current_user.id, session)
    if conversation.deleted_at is None:
        if conversation.resume_id is not None:
            await delete_resume(conversation.resume_id, current_user.id, session, storage)
            conversation.resume_id = None
        conversation.deleted_at = datetime.now(UTC)
        await session.commit()
