from datetime import datetime
from typing import Literal
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


class JobFitRead(JobRead):
    fit_score: float | None
    matched_skills: list[str]
    jd_skills_missing_from_resume: list[str] = Field(default_factory=list)
    validation_status: Literal["ok", "thin_description"]
    matching_policy_version: str


class ChatSearchRequest(BaseModel):
    query: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    work_mode: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=100)
    since_days: int | None = Field(default=None, ge=1, le=90)
    use_resume_skills: bool = True
    min_fit_score: float | None = Field(default=None, ge=0.0, le=5.0)
    conversation_id: UUID | None = None


class ChatSearchResponse(BaseModel):
    jobs: list[JobFitRead]
    skills_considered: list[str]
    resume_id: UUID | None
    feed_stale: bool
