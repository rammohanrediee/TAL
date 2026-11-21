"""Shared ingestion and user-scoped discovery for public job boards."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tal.features.jobs.entities import JobBoard, JobPosting, JobScan, JobWatch
from tal.features.jobs.providers import BoardSource, fetch_jobs, parse_board_url

SCAN_COOLDOWN = timedelta(minutes=5)


async def watch_board(session: AsyncSession, user_id: UUID, board_url: str) -> JobBoard:
    source = parse_board_url(board_url)
    result = await session.execute(
        select(JobBoard).where(JobBoard.provider == source.provider, JobBoard.slug == source.slug)
    )
    board = result.scalar_one_or_none()
    if board is None:
        board = JobBoard(
            provider=source.provider,
            slug=source.slug,
            board_url=source.board_url,
            company_name=source.slug.replace("-", " ").title(),
        )
        session.add(board)
        await session.flush()
    watched = await session.scalar(
        select(JobWatch.id).where(JobWatch.user_id == user_id, JobWatch.board_id == board.id)
    )
    if watched is None:
        session.add(JobWatch(user_id=user_id, board_id=board.id))
    await session.commit()
    return board


async def list_watches(session: AsyncSession, user_id: UUID) -> list[JobBoard]:
    result = await session.execute(
        select(JobBoard)
        .join(JobWatch, JobWatch.board_id == JobBoard.id)
        .where(JobWatch.user_id == user_id)
        .order_by(JobBoard.company_name)
    )
    return list(result.scalars().all())


async def unwatch_board(session: AsyncSession, user_id: UUID, board_id: UUID) -> bool:
    watch = await session.scalar(
        select(JobWatch).where(JobWatch.user_id == user_id, JobWatch.board_id == board_id)
    )
    if watch is None:
        return False
    await session.delete(watch)
    await session.commit()
    return True


async def scan_board(session: AsyncSession, board: JobBoard, *, force: bool = False) -> JobScan:
    now = datetime.now(UTC)
    last = board.last_scanned_at
    if not force and last and now - last.replace(tzinfo=UTC) < SCAN_COOLDOWN:
        return JobScan(board_id=board.id, status="skipped", found_count=0)
    scan = JobScan(board_id=board.id, status="running")
    session.add(scan)
    await session.commit()
    try:
        feed = await fetch_jobs(BoardSource(board.provider, board.slug, board.board_url))
        scan.source_snapshot = feed.source_snapshot
        seen: set[str] = set()
        for found in feed.jobs:
            seen.add(found.external_id)
            posting = await session.scalar(
                select(JobPosting).where(
                    JobPosting.board_id == board.id, JobPosting.external_id == found.external_id
                )
            )
            if posting is None:
                posting = JobPosting(
                    board_id=board.id,
                    external_id=found.external_id,
                    title=found.title,
                    job_url=found.job_url,
                    apply_url=found.apply_url,
                )
                session.add(posting)
            posting.title = found.title
            posting.location = found.location
            posting.work_mode = found.work_mode
            posting.employment_type = found.employment_type
            posting.description = found.description
            posting.job_url = found.job_url
            posting.apply_url = found.apply_url
            posting.is_live = True
            posting.last_seen_at = now
            posting.last_verified_at = now
        existing = await session.execute(
            select(JobPosting).where(JobPosting.board_id == board.id, JobPosting.is_live.is_(True))
        )
        for posting in existing.scalars():
            if posting.external_id not in seen:
                posting.is_live = False
                posting.last_verified_at = now
        board.last_error = None
        scan.status = "success"
        scan.found_count = len(seen)
    except Exception as error:
        await session.rollback()
        restored_board = await session.get(JobBoard, board.id)
        restored_scan = await session.get(JobScan, scan.id)
        assert restored_board is not None and restored_scan is not None
        board = restored_board
        scan = restored_scan
        board.last_error = str(error)[:300]
        scan.status = "failed"
        scan.error = board.last_error
    board.last_scanned_at = now
    await session.commit()
    return scan


async def scan_watches(session: AsyncSession, user_id: UUID) -> list[JobScan]:
    boards = await list_watches(session, user_id)
    return [await scan_board(session, board) for board in boards]


async def scan_all_boards(session: AsyncSession) -> list[JobScan]:
    boards = list(
        (
            await session.execute(
                select(JobBoard)
                .join(JobWatch, JobWatch.board_id == JobBoard.id)
                .distinct()
                .order_by(JobBoard.created_at)
            )
        ).scalars()
    )
    return [await scan_board(session, board) for board in boards]


async def list_jobs(
    session: AsyncSession,
    user_id: UUID,
    *,
    query: str | None = None,
    location: str | None = None,
    work_mode: str | None = None,
    company: str | None = None,
    since_days: int | None = None,
    live_only: bool = True,
) -> list[tuple[JobPosting, JobBoard]]:
    statement = (
        select(JobPosting, JobBoard)
        .join(JobBoard, JobPosting.board_id == JobBoard.id)
        .join(JobWatch, JobWatch.board_id == JobBoard.id)
        .where(JobWatch.user_id == user_id)
    )
    if live_only:
        statement = statement.where(JobPosting.is_live.is_(True))
    if query:
        statement = statement.where(
            or_(
                JobPosting.title.ilike(f"%{query}%"),
                JobBoard.company_name.ilike(f"%{query}%"),
            )
        )
    if location:
        statement = statement.where(JobPosting.location.ilike(f"%{location}%"))
    if work_mode:
        statement = statement.where(JobPosting.work_mode.ilike(f"%{work_mode}%"))
    if company:
        statement = statement.where(JobBoard.company_name.ilike(f"%{company}%"))
    if since_days:
        statement = statement.where(
            JobPosting.first_seen_at >= datetime.now(UTC) - timedelta(days=since_days)
        )
    result = await session.execute(statement.order_by(JobPosting.last_seen_at.desc()).limit(100))
    return list(result.all())
