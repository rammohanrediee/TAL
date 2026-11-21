"""Associate a processed résumé with a chat conversation."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2b72026chat_resume"
down_revision: str | Sequence[str] | None = "c1a72026chat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("resume_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_conversations_resume_id", "conversations", "resumes", ["resume_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_conversations_resume_id", "conversations", type_="foreignkey")
    op.drop_column("conversations", "resume_id")
