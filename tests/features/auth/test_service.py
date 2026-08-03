from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from tal.features.auth.errors import AccountLinkRequiredError
from tal.features.auth.security import hash_password
from tal.features.auth.service import get_or_create_external_user
from sqlalchemy.ext.asyncio import AsyncSession
from tal.features.auth.service import find_external_user
from tal.db.base import Base
from tal.features.auth.entities import User
from tal.features.auth.errors import EmailAlreadyRegisteredError
from tal.features.auth.schemas import UserRegister
from tal.features.auth.security import verify_password
from tal.features.auth.service import register
from unittest.mock import AsyncMock
from tal.features.auth.entities import ExternalAccount
from tal.features.auth.service import create_external_user
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tal.features.auth.entities import User
from tal.features.auth.errors import InvalidCredentialsError
from tal.features.auth.service import authenticate_user

@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


async def test_register_persists_user(db_session: AsyncSession) -> None:
    payload = UserRegister(
        email="buddy@gmail.com",
        password="buddy@124",
    )

    result = await register(payload, db_session)
    stored_user = await db_session.get(User, result.id)

    assert stored_user is not None
    assert stored_user.email == "buddy@gmail.com"
    assert stored_user.password_hash is not None
    assert stored_user.password_hash != payload.password
    assert verify_password(payload.password, stored_user.password_hash)
    assert not hasattr(result, "password_hash")


async def test_register_rejects_duplicate_email(
    db_session: AsyncSession,
) -> None:
    first_payload = UserRegister(
        email="Buddy@Example.COM",
        password="securepass123",
    )
    duplicate_payload = UserRegister(
        email="buddy@example.com",
        password="anotherpass123",
    )

    await register(first_payload, db_session)

    with pytest.raises(EmailAlreadyRegisteredError):
        await register(duplicate_payload, db_session)

    result = await db_session.execute(select(User))
    users = result.scalars().all()

    assert len(users) == 1
    assert users[0].email == "buddy@example.com"

async def test_password_login_rejects_google_only_user() -> None:
    user = User(
        email="google-user@example.com",
        password_hash=None,
    )

    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = user

    with pytest.raises(InvalidCredentialsError):
        await authenticate_user(
            email="google-user@example.com",
            password="any-password",
            session=session,
        )

async def test_find_external_user_returns_linked_user()->None:
    linked_user=User(
        email="buddy@gmail.com",
        password_hash=None,
    )
    session=AsyncMock(spec=AsyncSession)
    session.scalar.return_value=linked_user
    result=await find_external_user(
        provider="google",
        provider_subject="google_user-123",
        session=session,
    )
    assert result is linked_user

async def test_find_external_user_returns_not_linked()->None:
    session=AsyncMock(spec=AsyncSession)
    session.scalar.return_value=None
    result=await find_external_user(
        provider="google",
        provider_subject="unknown-google-user",
        session=session,
    )
    assert result is None

async def test_create_external_user_persists_user_and_link(db_session:AsyncSession,
                                                           )->None:
    user=await create_external_user(
        provider="GOOGLE",
        provider_subject="google-user-123",
        email="buddy@gmail.com",
        session=db_session,
    )
    external_account=await db_session.scalar(
        select(ExternalAccount).where(
            ExternalAccount.provider=="google",
            ExternalAccount.provider_subject=="google-user-123"
        )
    )
    assert user.email=="buddy@gmail.com"
    assert user.password_hash is None
    assert external_account is not None
    assert external_account.user_id==user.id
    assert external_account.provider_email=="buddy@gmail.com"

async def test_external_login_does_not_auto_link_existing_email(
    db_session: AsyncSession,
) -> None:
    existing_user = User(
        email="buddy@example.com",
        password_hash=hash_password("securepass123"),
    )
    db_session.add(existing_user)
    await db_session.commit()

    with pytest.raises(AccountLinkRequiredError):
        await get_or_create_external_user(
            provider="google",
            provider_subject="new-google-subject",
            email="Buddy@Example.COM",
            session=db_session,
        )