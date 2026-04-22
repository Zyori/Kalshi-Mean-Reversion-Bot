"""add market context columns for opening lines and trades

Revision ID: 37e71f7b5a29
Revises: 91f9f95b5f6d
Create Date: 2026-04-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "37e71f7b5a29"
down_revision: Union[str, Sequence[str], None] = "91f9f95b5f6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.add_column(sa.Column("opening_spread_home", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("opening_spread_away", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("opening_total", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("opening_home_team_total", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("opening_away_team_total", sa.Float(), nullable=True))

    with op.batch_alter_table("opening_lines", schema=None) as batch_op:
        batch_op.add_column(sa.Column("home_spread", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("away_spread", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("total_points", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("home_team_total", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("away_team_total", sa.Float(), nullable=True))

    with op.batch_alter_table("paper_trades", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("market_category", sa.String(length=20), nullable=False, server_default="moneyline")
        )


def downgrade() -> None:
    with op.batch_alter_table("paper_trades", schema=None) as batch_op:
        batch_op.drop_column("market_category")

    with op.batch_alter_table("opening_lines", schema=None) as batch_op:
        batch_op.drop_column("away_team_total")
        batch_op.drop_column("home_team_total")
        batch_op.drop_column("total_points")
        batch_op.drop_column("away_spread")
        batch_op.drop_column("home_spread")

    with op.batch_alter_table("games", schema=None) as batch_op:
        batch_op.drop_column("opening_away_team_total")
        batch_op.drop_column("opening_home_team_total")
        batch_op.drop_column("opening_total")
        batch_op.drop_column("opening_spread_away")
        batch_op.drop_column("opening_spread_home")
