from pwdlib import PasswordHash
from datetime import UTC,datetime,timedelta
from uuid import UUID
import jwt
from tal.core.config import settings
from jwt.exceptions import InvalidTokenError

from tal.features.auth.errors import InvalidCredentialsError

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id:UUID)->str:
    expries_at=datetime.now(UTC)+timedelta(
        minutes=settings.access_token_expire_minutes)
    payload={
        "sub":str(user_id),
        "exp":expries_at,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

def decode_access_token(token:str)->UUID:
    try:
        payload=jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        subject=payload.get("sub")
        if subject is None:
            raise InvalidTokenError()
        return UUID(subject) 
    except(InvalidTokenError,ValueError) as error:
        raise InvalidCredentialsError() from error