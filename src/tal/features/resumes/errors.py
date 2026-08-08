from tal.core.errors import DomainError


class EmptyResumeError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="empty_resume",
            message="The uploaded résumé is empty.",
            status_code=400,
        )


class ResumeTooLargeError(DomainError):
    def __init__(self, max_bytes: int) -> None:
        super().__init__(
            code="resume_too_large",
            message=f"Résumé must not exceed {max_bytes} bytes.",
            status_code=413,
        )


class UnsupportedResumeTypeError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="unsupported_resume_type",
            message="Only valid PDF and DOCX résumés are supported.",
            status_code=415,
        )


class InvalidResumeFilenameError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="invalid_resume_filename",
            message="The résumé filename is missing or invalid.",
            status_code=400,
        )

class ResumeNotFoundError(DomainError):
    def __init__(self):
        super().__init__(
            code="resume_not_found",
            message="Resume not found",
            status_code=404)