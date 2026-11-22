"""Add conversation search context for multi-turn job chat."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b22026chat_ctx"
down_revision: str | Sequence[str] | None = "f4d12026public_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("search_context", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "search_context")