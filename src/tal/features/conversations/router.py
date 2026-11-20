from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tal.core.config import settings
from tal.db.session import get_db_session
from tal.features.auth.dependencies import get_current_user
from tal.features.auth.entities import User
from tal.features.conversations.entities import Conversation
from tal.features.conversations.schemas import ChatConnectionToken, ConversationRead

router = APIRouter(prefix="/conversations")


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


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    conversation = await owned_conversation(conversation_id, current_user.id, session)
    if conversation.deleted_at is None:
        conversation.deleted_at = datetime.now(UTC)
        await session.commit()
