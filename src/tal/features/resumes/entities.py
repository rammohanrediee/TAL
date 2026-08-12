from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
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
from tal.features.resumes.models import ResumeStatus


class Resume(Base):
    __tablename__ = "resumes"
    id:Mapped[UUID] = mapped_column(
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
    updated_at:Mapped[datetime] = mapped_column(
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