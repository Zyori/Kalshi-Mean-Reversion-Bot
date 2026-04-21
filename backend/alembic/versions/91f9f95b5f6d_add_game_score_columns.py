"""add game score columns

Revision ID: 91f9f95b5f6d
Revises: 0946e9c41cee
Create Date: 2026-04-21 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "91f9f95b5f6d"
down_revision: Union[str, Sequence[str], None] = "0946e9c41cee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.add_column(sa.Column("latest_home_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("latest_away_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("final_home_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("final_away_score", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.drop_column("final_away_score")
        batch_op.drop_column("final_home_score")
        batch_op.drop_column("latest_away_score")
        batch_op.drop_column("latest_home_score")
