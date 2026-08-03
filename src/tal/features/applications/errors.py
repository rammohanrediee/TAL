from tal.core.errors import DomainError


class ApplicationNotFoundError(DomainError):
    def __init__(self, application_id: object) -> None:
        super().__init__(
            code="application_not_found",
            message=f"Application not found {application_id}",
            status_code=404,
        )
        self.application_id = application_id


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