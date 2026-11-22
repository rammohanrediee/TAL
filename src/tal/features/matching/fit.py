import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from tal.features.jobs.entities import JobPosting
from tal.features.skills.taxonomy import SKILLS_V1_ENTRIES

FIT_POLICY_VERSION = "fit-v1"
MIN_DESCRIPTION_CHARS = 200
MAX_VERIFIED_AGE_DAYS = 14
THIN_DESCRIPTION_SCORE_CAP = 2.5
MAX_DESCRIPTION_CHARS = 12_000

ValidationStatus = Literal["ok", "thin_description", "rejected"]


@dataclass(frozen=True, slots=True)
class FitResult:
    fit_score: float | None
    matched_skills: tuple[str, ...]
    jd_skills_missing_from_resume: tuple[str, ...]
    validation_status: ValidationStatus
    matching_policy_version: str


def _comparison_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _skill_search_terms(skill_label: str) -> frozenset[str]:
    terms = {_comparison_text(skill_label)}
    token = _comparison_text(skill_label)
    for entry in SKILLS_V1_ENTRIES:
        aliases = {_comparison_text(entry.name), _comparison_text(entry.key)} | {
            _comparison_text(alias) for alias in entry.aliases
        }
        if token in aliases:
            terms.add(_comparison_text(entry.name))
            terms.add(_comparison_text(entry.key))
            terms.update(_comparison_text(alias) for alias in entry.aliases)
    return frozenset(term for term in terms if term)


def _mentions_term(text: str, term: str) -> bool:
    if not term:
        return False
    pattern = r"(?<![\w#+./-])" + re.escape(term) + r"(?![\w#+./-])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _mentions_skill(skill_label: str, text: str) -> bool:
    return any(_mentions_term(text, term) for term in _skill_search_terms(skill_label))


def validate_posting(posting: JobPosting, *, now: datetime | None = None) -> ValidationStatus:
    moment = now or datetime.now(UTC)
    if not posting.is_live:
        return "rejected"
    if not posting.title.strip() or not posting.job_url.strip() or not posting.apply_url.strip():
        return "rejected"
    verified_at = posting.last_verified_at
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)
    if moment - verified_at > timedelta(days=MAX_VERIFIED_AGE_DAYS):
        return "rejected"
    description = (posting.description or "").strip()
    if len(description) < MIN_DESCRIPTION_CHARS:
        return "thin_description"
    return "ok"


def taxonomy_terms_in_text(text: str) -> tuple[str, ...]:
    found: list[str] = []
    normalized = _comparison_text(text)
    for entry in SKILLS_V1_ENTRIES:
        labels = (entry.name, *entry.aliases)
        if any(_mentions_term(normalized, _comparison_text(label)) for label in labels):
            found.append(entry.name)
    return tuple(dict.fromkeys(found))


def compute_fit(
    user_skills: tuple[str, ...],
    *,
    title: str,
    description: str | None,
    validation_status: ValidationStatus,
) -> FitResult:
    if validation_status == "rejected":
        return FitResult(
            fit_score=None,
            matched_skills=(),
            jd_skills_missing_from_resume=(),
            validation_status=validation_status,
            matching_policy_version=FIT_POLICY_VERSION,
        )

    if not user_skills:
        return FitResult(
            fit_score=None,
            matched_skills=(),
            jd_skills_missing_from_resume=taxonomy_terms_in_text(
                _comparison_text(f"{title}\n{(description or '')[:MAX_DESCRIPTION_CHARS]}")
            ),
            validation_status=validation_status,
            matching_policy_version=FIT_POLICY_VERSION,
        )

    title_text = _comparison_text(title)
    body_text = _comparison_text(f"{title}\n{(description or '')[:MAX_DESCRIPTION_CHARS]}")

    matched: list[str] = []
    weighted = 0.0
    max_weight = max(1, len(user_skills)) * 2.0

    for skill in user_skills:
        if not _mentions_skill(skill, body_text):
            continue
        matched.append(skill)
        weighted += 2.0 if _mentions_skill(skill, title_text) else 1.0

    ratio = weighted / max_weight
    fit_score = round(min(5.0, ratio * 5.0), 1)
    if validation_status == "thin_description":
        fit_score = min(fit_score, THIN_DESCRIPTION_SCORE_CAP)

    jd_skills = taxonomy_terms_in_text(body_text)
    matched_cf = {_comparison_text(skill) for skill in matched}
    missing = tuple(
        skill
        for skill in jd_skills
        if _comparison_text(skill) not in matched_cf
        and not any(
            _comparison_text(skill) in _comparison_text(user_skill) for user_skill in user_skills
        )
    )

    return FitResult(
        fit_score=fit_score,
        matched_skills=tuple(matched),
        jd_skills_missing_from_resume=missing,
        validation_status=validation_status,
        matching_policy_version=FIT_POLICY_VERSION,
    )