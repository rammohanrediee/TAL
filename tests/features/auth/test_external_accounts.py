from sqlalchemy import UniqueConstraint

from tal.features.auth.entities import ExternalAccount
from tal.features.auth.entities import User

def test_provider_identity_is_unique() -> None:
    unique_column_sets = {
        tuple(constraint.columns.keys())
        for constraint in ExternalAccount.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("provider", "provider_subject") in unique_column_sets

def test_external_account_does_not_store_oauth_tokens() -> None:
    column_names = set(ExternalAccount.__table__.columns.keys())

    assert "access_token" not in column_names
    assert "refresh_token" not in column_names
    assert "id_token" not in column_names


def test_user_password_hash_is_optional_for_external_login() -> None:
    password_hash = User.__table__.columns["password_hash"]

    assert password_hash.nullable is True