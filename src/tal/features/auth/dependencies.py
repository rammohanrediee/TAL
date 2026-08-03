from typing import Annotated

from fastapi import Depends,Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from tal.db.session import get_db_session
from tal.features.auth.entities import User
from tal.features.auth.errors import InvalidCredentialsError
from tal.features.auth.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False
)

async def get_current_user(request:Request,token:Annotated[str,Depends(oauth2_scheme)],
                           session:Annotated[AsyncSession,Depends(get_db_session)],)->User:
    access_token=token or request.cookies.get("tal_access_token")
    if access_token is None:
        raise InvalidCredentialsError()
    user_id=decode_access_token(access_token)
    user=await session.get(User,user_id)
    if user is None or not user.is_active:
        raise InvalidCredentialsError()
    return user