
from uuid import UUID, uuid4
from datetime import UTC, datetime
import uuid
from tal.db.base import Base
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
class User(Base):
    __tablename__="users"
    id: Mapped[UUID] = mapped_column(
            Uuid,
            primary_key=True,
            default=uuid4,
        )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str| None]=mapped_column(String(255),nullable=True)
    is_active:Mapped[bool]=mapped_column(default=True,nullable=False)
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

class ExternalAccount(Base):
    __tablename__="externalAccounts"
    __table_args__ = (
    UniqueConstraint(
        "provider",
        "provider_subject",
        name="uq_external_accounts_provider_subject",
    ),)

    id:Mapped[UUID]=mapped_column(Uuid,primary_key=True,default=uuid4)
    user_id:Mapped[UUID] =mapped_column(
        ForeignKey("users.id",ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider:Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    provider_subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    provider_email:Mapped[str| None]
    created_at:Mapped[datetime] = mapped_column(
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
    