from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from tal.features.auth.security import hash_password, verify_password
from tal.features.auth.schemas import UserRead, UserRegister,UserLogin
from sqlalchemy.ext.asyncio import AsyncSession
from tal.features.auth.entities import User
from tal.features.auth.entities import ExternalAccount, User
from tal.features.auth.errors import EmailAlreadyRegisteredError, InvalidCredentialsError,AccountLinkRequiredError
async def register(payload:UserRegister,
                   session:AsyncSession,)->UserRead:
    data=payload.model_dump()
    data["email"] = str(data["email"]).strip().lower()
    data["password_hash"]=hash_password(data.pop("password"))
    existing_user=await session.scalar(
        select(User).where (User.email==data["email"])
    )
    if existing_user is not None:
        raise EmailAlreadyRegisteredError()
    user = User(**data)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise EmailAlreadyRegisteredError() from None
    await session.refresh(user)
    return UserRead.model_validate(user)

async def authenticate_user(email:str,
                            password:str,
                            session:AsyncSession)->User:
    normalized_email=email.strip().lower()
    user=await session.scalar(
        select(User).where (User.email==normalized_email)
    )
    if user is None or user.password_hash is None:
        raise InvalidCredentialsError()
    if not verify_password(password,user.password_hash):
        raise InvalidCredentialsError()
    if not user.is_active:
        raise InvalidCredentialsError()
    return user

async def find_external_user(provider:str,provider_subject:str,
                             session:AsyncSession,)->User | None:
    normalized_provider=provider.strip().lower()
    return await session.scalar(
        select(User)
        .join(
            ExternalAccount,
            ExternalAccount.user_id==User.id,
        )
        .where(
            ExternalAccount.provider==normalized_provider,
            ExternalAccount.provider_subject==provider_subject,
        )
    )

async def create_external_user(provider:str,provider_subject:str,
                               email:str,
                               session:AsyncSession)->User:
    normalized_provider=provider.strip().lower()
    normalized_email=email.strip().lower()
    user=User(
        email=normalized_email,
        password_hash=None,

    )
    session.add(user)
    await session.flush()
    external_account=ExternalAccount(
        user_id=user.id,
        provider=normalized_provider,
        provider_subject=provider_subject,
        provider_email=normalized_email,
    )
    session.add(external_account)
    await session.commit()
    await session.refresh(user)
    return user

async def get_or_create_external_user(provider:str,provider_subject:str, 
                                      email:str,
                                      session:AsyncSession,)-> User:
    linked_user=await find_external_user(
        provider=provider,
        provider_subject=provider_subject,
        session=session
    )
    if linked_user is not None:
        return linked_user

    normalized_email=email.strip().lower()
    existing_email_user=await session.scalar(
        select(User).where(User.email==normalized_email)
    )
    if existing_email_user is not None:
        raise AccountLinkRequiredError()
    return await create_external_user(
        provider=provider,
        provider_subject=provider_subject,
        email=normalized_email,
        session=session,
    )