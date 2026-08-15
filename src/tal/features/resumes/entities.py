from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from tal.db.base import Base
from tal.features.resumes.models import (
    EvidenceStatus,
    EvidenceType,
    ResumeStatus,
)
from tal.features.skills.models import SkillMatchType


class Resume(Base):
    __tablename__ = "resumes"
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    status: Mapped[ResumeStatus] = mapped_column(
        SqlEnum(
            ResumeStatus,
            name="resume_status",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=ResumeStatus.UPLOADED,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        unique=True,
    )
    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ResumeTextBlock(Base):
    __tablename__ = "resume_text_blocks"
    __table_args__ = (
        UniqueConstraint(
            "resume_id",
            "ordinal",
            name="uq_resume_text_blocks_resume_ordinal",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    resume_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "resumes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    paragraph_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )


class ResumeEvidence(Base):
    __tablename__ = "resume_evidence"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    resume_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "resumes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    source_block_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "resume_text_blocks.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(
        SqlEnum(
            EvidenceType,
            name="evidence_type",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )
    status: Mapped[EvidenceStatus] = mapped_column(
        SqlEnum(
            EvidenceStatus,
            name="evidence_status",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=EvidenceStatus.PENDING,
    )
    extracted_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    corrected_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    canonical_skill_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    canonical_skill_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    skill_match_type: Mapped[SkillMatchType | None] = mapped_column(
        SqlEnum(
            SkillMatchType,
            name="skill_match_type",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=True,
    )
    skill_taxonomy_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
