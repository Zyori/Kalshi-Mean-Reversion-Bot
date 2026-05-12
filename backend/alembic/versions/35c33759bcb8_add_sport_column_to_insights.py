"""add sport column to insights

Revision ID: 35c33759bcb8
Revises: b4a18bd69107
Create Date: 2026-05-12 18:06:38.934206

Adds an optional sport attribution to insights so per-sport overview pages
can surface their own findings without leaking into other sports' views.
Existing rows leave it NULL — those represent cross-sport meta-findings.

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "35c33759bcb8"
down_revision: Union[str, Sequence[str], None] = "b4a18bd69107"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("insights", sa.Column("sport", sa.String(length=20), nullable=True))
    op.create_index(
        "ix_insights_sport_created", "insights", ["sport", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_insights_sport_created", table_name="insights")
    op.drop_column("insights", "sport")
