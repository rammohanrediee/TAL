import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from tal.core.config import settings
from tal.db.session import get_db_session
from tal.features.auth.dependencies import get_current_user
from tal.features.auth.entities import User
from tal.features.jobs import service
from tal.features.jobs.entities import JobBoard, JobScan
from tal.features.jobs.chat_search import ChatSearchFilters, chat_search_jobs
from tal.features.jobs.schemas import (
    BoardRead,
    ChatSearchRequest,
    ChatSearchResponse,
    JobRead,
    ScanRead,
    WatchCreate,
)
from tal.features.matching.profile import ProfileSummary, build_profile_summary

router = APIRouter(prefix="/jobs", tags=["jobs"])


def board_read(board: JobBoard) -> BoardRead:
    return BoardRead(
        id=board.id,
        provider=board.provider,
        company_name=board.company_name,
        board_url=board.board_url,
        last_scanned_at=board.last_scanned_at,
        last_error=board.last_error,
    )


def scan_read(scan: JobScan) -> ScanRead:
    return ScanRead(
        board_id=scan.board_id, status=scan.status, found_count=scan.found_count, error=scan.error
    )


@router.get("/boards", response_model=list[BoardRead])
async def boards(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[BoardRead]:
    return [board_read(board) for board in await service.list_watches(session, user.id)]


@router.get("/catalog", response_model=list[BoardRead])
async def catalog(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[BoardRead]:
    return [board_read(board) for board in await service.list_catalog(session)]


@router.post("/boards", response_model=BoardRead, status_code=status.HTTP_201_CREATED)
async def watch(
    payload: WatchCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BoardRead:
    try:
        return board_read(await service.watch_board(session, user.id, payload.board_url))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unwatch(
    board_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    if not await service.unwatch_board(session, user.id, board_id):
        raise HTTPException(status_code=404, detail="Board not found")


@router.post("/scan", response_model=list[ScanRead])
async def scan(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ScanRead]:
    return [scan_read(item) for item in await service.scan_watches(session, user.id)]


@router.post("/internal/scan", response_model=list[ScanRead], include_in_schema=False)
async def scheduled_scan(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_tal_scan_key: Annotated[str | None, Header()] = None,
) -> list[ScanRead]:
    if not x_tal_scan_key or not secrets.compare_digest(
        x_tal_scan_key, settings.job_scan_secret.get_secret_value()
    ):
        raise HTTPException(status_code=404, detail="Not found")
    return [scan_read(item) for item in await service.scan_all_boards(session)]


@router.post("/chat-search", response_model=ChatSearchResponse)
async def chat_search(
    payload: ChatSearchRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatSearchResponse:
    result = await chat_search_jobs(
        session,
        user.id,
        conversation_id=payload.conversation_id,
        filters=ChatSearchFilters(
            query=payload.query,
            location=payload.location,
            work_mode=payload.work_mode,
            company=payload.company,
            since_days=payload.since_days,
            use_resume_skills=payload.use_resume_skills,
            min_fit_score=payload.min_fit_score,
        ),
    )
    await session.commit()
    return ChatSearchResponse(
        jobs=list(result.jobs),
        skills_considered=list(result.skills_considered),
        resume_id=result.resume_id,
        feed_stale=result.feed_stale,
    )


@router.post("/internal/chat-search", response_model=ChatSearchResponse, include_in_schema=False)
async def internal_chat_search(
    payload: ChatSearchRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_tal_chat_tool_key: Annotated[str | None, Header()] = None,
    x_tal_user_id: Annotated[str | None, Header()] = None,
) -> ChatSearchResponse:
    if not x_tal_chat_tool_key or not secrets.compare_digest(
        x_tal_chat_tool_key, settings.chat_tool_secret.get_secret_value()
    ):
        raise HTTPException(status_code=404, detail="Not found")
    if not x_tal_user_id:
        raise HTTPException(status_code=400, detail="Missing user")
    try:
        user_id = UUID(x_tal_user_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid user") from error
    result = await chat_search_jobs(
        session,
        user_id,
        conversation_id=payload.conversation_id,
        filters=ChatSearchFilters(
            query=payload.query,
            location=payload.location,
            work_mode=payload.work_mode,
            company=payload.company,
            since_days=payload.since_days,
            use_resume_skills=payload.use_resume_skills,
            min_fit_score=payload.min_fit_score,
        ),
    )
    await session.commit()
    return ChatSearchResponse(
        jobs=list(result.jobs),
        skills_considered=list(result.skills_considered),
        resume_id=result.resume_id,
        feed_stale=result.feed_stale,
    )


@router.get("/profile-summary", response_model=ProfileSummary)
async def job_profile_summary(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    conversation_id: UUID | None = None,
) -> ProfileSummary:
    return await build_profile_summary(session, user.id, conversation_id=conversation_id)


@router.get("/internal/profile-summary", response_model=ProfileSummary, include_in_schema=False)
async def internal_profile_summary(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    x_tal_chat_tool_key: Annotated[str | None, Header()] = None,
    x_tal_user_id: Annotated[str | None, Header()] = None,
    conversation_id: UUID | None = None,
) -> ProfileSummary:
    if not x_tal_chat_tool_key or not secrets.compare_digest(
        x_tal_chat_tool_key, settings.chat_tool_secret.get_secret_value()
    ):
        raise HTTPException(status_code=404, detail="Not found")
    if not x_tal_user_id:
        raise HTTPException(status_code=400, detail="Missing user")
    try:
        user_id = UUID(x_tal_user_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid user") from error
    return await build_profile_summary(session, user_id, conversation_id=conversation_id)


@router.get("", response_model=list[JobRead])
async def jobs(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[str | None, Query(max_length=100)] = None,
    location: Annotated[str | None, Query(max_length=100)] = None,
    work_mode: Annotated[str | None, Query(max_length=50)] = None,
    company: Annotated[str | None, Query(max_length=100)] = None,
    since_days: Annotated[int | None, Query(ge=1, le=90)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    live_only: bool = True,
) -> list[JobRead]:
    rows = await service.list_jobs(
        session,
        user.id,
        query=query,
        location=location,
        work_mode=work_mode,
        company=company,
        since_days=since_days,
        live_only=live_only,
        offset=offset,
    )
    return [
        JobRead(
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
        for posting, board in rows
    ]
