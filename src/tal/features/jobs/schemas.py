from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WatchCreate(BaseModel):
    board_url: str = Field(max_length=2048)


class BoardRead(BaseModel):
    id: UUID
    provider: str
    company_name: str
    board_url: str
    last_scanned_at: datetime | None
    last_error: str | None


class JobRead(BaseModel):
    id: UUID
    company_name: str
    provider: str
    title: str
    location: str | None
    work_mode: str | None
    employment_type: str | None
    description: str | None
    job_url: str
    apply_url: str
    is_live: bool
    first_seen_at: datetime
    last_verified_at: datetime


class ScanRead(BaseModel):
    board_id: UUID
    status: str
    found_count: int
    error: str | None
