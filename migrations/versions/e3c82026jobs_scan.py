"""Store shared public jobs and user board watches."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3c82026jobs_scan"
down_revision: str | Sequence[str] | None = "d2b72026chat_resume"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_boards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("board_url", sa.String(2048), nullable=False),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "slug", name="uq_job_board_source"),
    )
    op.create_table(
        "job_watches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "board_id",
            sa.Uuid(),
            sa.ForeignKey("job_boards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "board_id", name="uq_job_watch_user_board"),
    )
    op.create_index("ix_job_watches_user_id", "job_watches", ["user_id"])
    op.create_index("ix_job_watches_board_id", "job_watches", ["board_id"])
    op.create_table(
        "job_postings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "board_id",
            sa.Uuid(),
            sa.ForeignKey("job_boards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("location", sa.String(300)),
        sa.Column("work_mode", sa.String(24)),
        sa.Column("employment_type", sa.String(80)),
        sa.Column("description", sa.Text()),
        sa.Column("job_url", sa.String(2048), nullable=False),
        sa.Column("apply_url", sa.String(2048), nullable=False),
        sa.Column("is_live", sa.Boolean(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("board_id", "external_id", name="uq_job_posting_source_id"),
    )
    op.create_index("ix_job_postings_board_id", "job_postings", ["board_id"])
    op.create_table(
        "job_scans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "board_id",
            sa.Uuid(),
            sa.ForeignKey("job_boards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("found_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(300)),
        sa.Column("source_snapshot", sa.LargeBinary()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_scans_board_id", "job_scans", ["board_id"])


def downgrade() -> None:
    op.drop_table("job_scans")
    op.drop_table("job_postings")
    op.drop_table("job_watches")
    op.drop_table("job_boards")
