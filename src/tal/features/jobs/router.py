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
from tal.features.jobs.schemas import BoardRead, JobRead, ScanRead, WatchCreate

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
        x_tal_scan_key, settings.jwt_secret_key.get_secret_value()
    ):
        raise HTTPException(status_code=404, detail="Not found")
    return [scan_read(item) for item in await service.scan_all_boards(session)]


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
