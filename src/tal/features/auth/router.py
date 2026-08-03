from typing import Annotated, cast

from authlib.integrations.base_client.errors import OAuthError  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from tal.core.config import settings
from tal.db.session import get_db_session
from tal.features.auth.dependencies import get_current_user
from tal.features.auth.entities import User
from tal.features.auth.errors import InvalidCredentialsError
from tal.features.auth.oauth import oauth
from tal.features.auth.schemas import (
    GoogleIdentityRead,
    TokenResponse,
    UserRead,
    UserRegister,
)
from tal.features.auth.security import create_access_token
from tal.features.auth.service import authenticate_user,get_or_create_external_user
from tal.features.auth.service import register as register_service
from fastapi import Request,Response,status
router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> UserRead:
    return await register_service(payload, session)


@router.post("/token", response_model=TokenResponse)
async def issue_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    user = await authenticate_user(
        email=form_data.username,
        password=form_data.password,
        session=session,
    )
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get("/google/login", response_class=RedirectResponse)
async def google_login(request: Request) -> RedirectResponse:
    google = oauth.create_client("google")
    if google is None:
        raise RuntimeError("Google oauth client is not configured")
    return cast(
        RedirectResponse,
        await google.authorize_redirect(
            request,
            settings.google_redirect_uri,
        ),
    )


@router.get("/google/callback", response_model=TokenResponse)
async def google_callback(request: Request,
                          response:Response,session:Annotated[AsyncSession,Depends(get_db_session),],) -> TokenResponse:
    google = oauth.create_client("google")
    if google is None:
        raise RuntimeError("Google OAuth client is not configured")
    try:
        token = await google.authorize_access_token(request)
    except OAuthError as error:
        raise InvalidCredentialsError() from error
    user_info = token.get("userinfo")
    if user_info is None:
        raise InvalidCredentialsError()
    provider_user_id = user_info.get("sub")
    email = user_info.get("email")
    email_verified = user_info.get("email_verified")
    if not provider_user_id or not email or email_verified is not True:
        raise InvalidCredentialsError()
    user=await get_or_create_external_user(
        provider="google",
        provider_subject=provider_user_id,
        email=email,
        session=session,
    )
    tal_acess_token=create_access_token(user.id)
    response.set_cookie(
    key="tal_access_token",
    value=tal_acess_token,
    httponly=True,
    secure=True,
    samesite="lax",
    path="/",
    max_age=settings.access_token_expire_minutes * 60,

    )
    return TokenResponse(
        access_token=tal_acess_token
    )


@router.post("/logout",status_code=status.HTTP_204_NO_CONTENT)
async def logout(response:Response)->None:
    response.delete_cookie(
        key="tal_access_token",
        path="/",
        secure=True,
        httponly=True,
        samesite="lax"
    )
