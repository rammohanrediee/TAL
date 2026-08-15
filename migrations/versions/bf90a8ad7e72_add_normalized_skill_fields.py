"""add normalized skill fields

Revision ID: bf90a8ad7e72
Revises: 84acdf65bde6
Create Date: 2026-08-14 15:58:46.196299

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bf90a8ad7e72"
down_revision: str | Sequence[str] | None = "84acdf65bde6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    skill_match_type = sa.Enum(
        "exact",
        "alias",
        "unmatched",
        name="skill_match_type",
    )
    skill_match_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "resume_evidence",
        sa.Column("canonical_skill_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "resume_evidence",
        sa.Column("canonical_skill_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "resume_evidence",
        sa.Column("skill_match_type", skill_match_type, nullable=True),
    )
    op.add_column(
        "resume_evidence",
        sa.Column("skill_taxonomy_version", sa.String(length=50), nullable=True),
    )
    op.create_index(
        op.f("ix_resume_evidence_canonical_skill_key"),
        "resume_evidence",
        ["canonical_skill_key"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_resume_evidence_canonical_skill_key"),
        table_name="resume_evidence",
    )
    op.drop_column("resume_evidence", "skill_taxonomy_version")
    op.drop_column("resume_evidence", "skill_match_type")
    op.drop_column("resume_evidence", "canonical_skill_name")
    op.drop_column("resume_evidence", "canonical_skill_key")

    sa.Enum(name="skill_match_type").drop(
        op.get_bind(),
        checkfirst=True,
    )
