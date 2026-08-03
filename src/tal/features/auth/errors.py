
from fastapi import status

from tal.core.errors import DomainError


class EmailAlreadyRegisteredError(DomainError):
    def __init__(self)-> None:
        super().__init__(
            code="email_already_registered",
            message="Email already registered",
            status_code=409,)

        
class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="invalid_credentials",
            message="Invalid credentials",
            status_code=status.HTTP_401_UNAUTHORIZED,
            )

class AccountLinkRequiredError(DomainError):
    def __init__(self)->None:
        super().__init__(
            code="account_link_required",
            message=(
                "An account with this email already exists"
                "sign in to link external account"
            ),
            status_code=409,
        )
