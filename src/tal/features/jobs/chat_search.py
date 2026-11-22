from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tal.features.conversations.entities import Conversation
from tal.features.jobs import service
from tal.features.jobs.entities import JobBoard, JobPosting
from tal.features.jobs.schemas import JobFitRead, JobRead
from tal.features.matching.fit import compute_fit, validate_posting
from tal.features.matching.skills import load_user_skill_labels, resolve_resume_id

CATALOG_STALE_HOURS = 24
CHAT_SEARCH_LIMIT = 25


@dataclass(frozen=True, slots=True)
class ChatSearchFilters:
    query: str | None = None
    location: str | None = None
    work_mode: str | None = None
    company: str | None = None
    since_days: int | None = None
    use_resume_skills: bool = True
    min_fit_score: float | None = None


@dataclass(frozen=True, slots=True)
class ChatSearchResult:
    jobs: tuple[JobFitRead, ...]
    skills_considered: tuple[str, ...]
    resume_id: UUID | None
    feed_stale: bool
    filters_applied: ChatSearchFilters


async def catalog_is_stale(session: AsyncSession) -> bool:
    result = await session.execute(
        select(func.max(JobBoard.last_scanned_at)).where(JobBoard.is_catalog.is_(True))
    )
    latest = result.scalar_one_or_none()
    if latest is None:
        return True
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    return datetime.now(UTC) - latest > timedelta(hours=CATALOG_STALE_HOURS)


def posting_to_job_read(posting: JobPosting, board: JobBoard) -> JobRead:
    return JobRead(
        id=posting.id,
        company_name=board.company_name,
        provider=board.provider,
        title=posting.title,
        location=posting.location,
        work_mode=posting.work_mode,
        employment_type=posting.employment_type,
        description=posting.description,
        job_url=posting.job_url,
        apply_url=posting.apply_url,
        is_live=posting.is_live,
        first_seen_at=posting.first_seen_at,
        last_verified_at=posting.last_verified_at,
    )


async def chat_search_jobs(
    session: AsyncSession,
    user_id: UUID,
    *,
    conversation_id: UUID | None,
    filters: ChatSearchFilters,
) -> ChatSearchResult:
    resume_id = await resolve_resume_id(session, user_id, conversation_id=conversation_id)
    skills: tuple[str, ...] = ()
    if filters.use_resume_skills and resume_id is not None:
        skills = await load_user_skill_labels(session, user_id, resume_id=resume_id)

    rows = await service.list_jobs(
        session,
        user_id,
        query=filters.query,
        location=filters.location,
        work_mode=filters.work_mode,
        company=filters.company,
        since_days=filters.since_days,
        live_only=True,
        offset=0,
        include_description_in_query=True,
        limit=CHAT_SEARCH_LIMIT * 3,
    )

    now = datetime.now(UTC)
    ranked: list[tuple[float, datetime, JobFitRead]] = []

    for posting, board in rows:
        validation_status = validate_posting(posting, now=now)
        if validation_status == "rejected":
            continue
        fit = compute_fit(
            skills,
            title=posting.title,
            description=posting.description,
            validation_status=validation_status,
        )
        if filters.min_fit_score is not None and (
            fit.fit_score is None or fit.fit_score < filters.min_fit_score
        ):
            continue
        fit_score = fit.fit_score if fit.fit_score is not None else -1.0
        job_base = posting_to_job_read(posting, board)
        ranked.append(
            (
                fit_score,
                posting.last_seen_at,
                JobFitRead(
                    **job_base.model_dump(),
                    fit_score=fit.fit_score,
                    matched_skills=list(fit.matched_skills),
                    jd_skills_missing_from_resume=list(fit.jd_skills_missing_from_resume),
                    validation_status=fit.validation_status,
                    matching_policy_version=fit.matching_policy_version,
                ),
            )
        )

    ranked.sort(key=lambda item: (-item[0], -item[1].timestamp(), str(item[2].id)))
    jobs = tuple(item[2] for item in ranked[:CHAT_SEARCH_LIMIT])

    if conversation_id is not None:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is not None and conversation.user_id == user_id:
            context = dict(conversation.search_context or {})
            context.update(
                {
                    "last_query": filters.query,
                    "last_location": filters.location,
                    "last_work_mode": filters.work_mode,
                    "last_company": filters.company,
                    "updated_at": now.isoformat(),
                }
            )
            conversation.search_context = context

    feed_stale = await catalog_is_stale(session)
    return ChatSearchResult(
        jobs=jobs,
        skills_considered=skills,
        resume_id=resume_id,
        feed_stale=feed_stale,
        filters_applied=filters,
    )