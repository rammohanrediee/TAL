from uuid import uuid4

import pytest

from tal.features.auth.errors import InvalidCredentialsError
from tal.features.auth.security import (
    create_access_token,
    decode_access_token,
)


def test_access_token_round_trip() -> None:
    user_id = uuid4()

    token = create_access_token(user_id)
    decoded_user_id = decode_access_token(token)

    assert decoded_user_id == user_id


def test_rejects_invalid_access_token() -> None:
    with pytest.raises(InvalidCredentialsError):
        decode_access_token("not-a-valid-token")


def test_rejects_tampered_access_token() -> None:
    token = create_access_token(uuid4())
    tampered_token = f"{token}x"

    with pytest.raises(InvalidCredentialsError):
        decode_access_token(tampered_token)