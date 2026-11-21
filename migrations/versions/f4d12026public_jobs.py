"""Mark starter job boards as a shared public catalog."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4d12026public_jobs"
down_revision: str | Sequence[str] | None = "e3c82026jobs_scan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_boards",
        sa.Column("is_catalog", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_job_boards_is_catalog", "job_boards", ["is_catalog"])


def downgrade() -> None:
    op.drop_index("ix_job_boards_is_catalog", table_name="job_boards")
    op.drop_column("job_boards", "is_catalog")
