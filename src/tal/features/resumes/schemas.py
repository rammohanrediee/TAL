from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tal.features.resumes.models import (
    EvidenceStatus,
    EvidenceType,
    ResumeStatus,
)
from tal.features.skills.models import SkillMatchType


class ResumeRead(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    status: ResumeStatus
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExtractedEvidenceCandidate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
    evidence_type: EvidenceType
    claim_text: str = Field(min_length=1)
    source_block_id: UUID
    source_quote: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class EvidenceSourceBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    text: str
    page_number: int | None = None
    paragraph_number: int | None = None


class EvidenceCandidateBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[ExtractedEvidenceCandidate]


class ResumeEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_id: UUID
    source_block_id: UUID
    evidence_type: EvidenceType
    status: EvidenceStatus
    extracted_text: str
    corrected_text: str | None
    confidence: float
    source_text: str
    canonical_skill_key: str | None
    canonical_skill_name: str | None
    skill_match_type: SkillMatchType | None
    skill_taxonomy_version: str | None
    created_at: datetime
    updated_at: datetime


class ResumeEvidenceCorrection(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    corrected_text: str = Field(
        min_length=1,
        max_length=2_000,
    )
