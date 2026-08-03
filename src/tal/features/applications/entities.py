from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from tal.db.base import Base
from tal.features.applications.models import ApplicationStatus


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
    company_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    role_title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SqlEnum(
            ApplicationStatus,
            name="application_status",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=ApplicationStatus.SAVED,
    )
    job_url: Mapped[str | None] = mapped_column(
        String(2048),
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
