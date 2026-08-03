import pytest

from tal.features.applications.models import ApplicationStatus


@pytest.mark.parametrize(
    ("raw_value", "expected_status"),
    [
        ("saved", ApplicationStatus.SAVED),
        ("applied", ApplicationStatus.APPLIED),
        ("offered", ApplicationStatus.OFFERED),
        ("rejected", ApplicationStatus.REJECTED),
        ("interviewing", ApplicationStatus.INTERVIEWING),
    ],
)
def test_application_status(
    raw_value: str,
    expected_status: ApplicationStatus,
) -> None:
    status = ApplicationStatus(raw_value)
    assert status is expected_status
    assert status.value == raw_value


def test_application_status_rejected_invalid_value() -> None:
    with pytest.raises(ValueError):
        ApplicationStatus("withdrawn")
