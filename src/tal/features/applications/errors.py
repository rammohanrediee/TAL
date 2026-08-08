from tal.core.errors import DomainError


class ApplicationNotFoundError(DomainError):
    def __init__(self, application_id: object) -> None:
        super().__init__(
            code="application_not_found",
            message=f"Application not found {application_id}",
            status_code=404,
        )
        self.application_id = application_id
