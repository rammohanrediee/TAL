from datetime import UTC, datetime
from uuid import uuid4

from tal.features.jobs.entities import JobPosting
from tal.features.matching.fit import compute_fit, validate_posting


def _posting(**overrides: object) -> JobPosting:
    now = datetime.now(UTC)
    base = {
        "board_id": uuid4(),
        "external_id": "1",
        "title": "Senior Python Engineer",
        "location": "Remote",
        "work_mode": "Remote",
        "employment_type": "Full-time",
        "description": "We need Python, FastAPI, and PostgreSQL experience. " * 5,
        "job_url": "https://example.com/jobs/1",
        "apply_url": "https://example.com/jobs/1/apply",
        "is_live": True,
        "first_seen_at": now,
        "last_seen_at": now,
        "last_verified_at": now,
    }
    base.update(overrides)
    return JobPosting(**base)  # type: ignore[arg-type]


def test_validate_rejects_stale_posting() -> None:
    old = datetime(2020, 1, 1, tzinfo=UTC)
    posting = _posting(last_verified_at=old)
    assert validate_posting(posting) == "rejected"


def test_compute_fit_scores_matching_skills() -> None:
    description = (
        "Looking for a backend engineer with Python, FastAPI, and PostgreSQL. "
        "You will ship APIs and work with React partners."
    )
    result = compute_fit(
        ("Python", "FastAPI", "PostgreSQL"),
        title="Backend Engineer",
        description=description,
        validation_status="ok",
    )
    assert result.fit_score is not None and result.fit_score >= 1.5
    assert "Python" in result.matched_skills
    assert "FastAPI" in result.matched_skills


def test_compute_fit_without_skills_returns_null_score() -> None:
    result = compute_fit(
        (),
        title="Engineer",
        description="Python required",
        validation_status="ok",
    )
    assert result.fit_score is None