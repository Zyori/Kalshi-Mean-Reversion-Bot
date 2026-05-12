"""add sport_configs and seed soccer-active others-passive

Revision ID: b4a18bd69107
Revises: 5af3e7d68c1b
Create Date: 2026-05-12 16:05:45.573023

Introduces the per-sport engagement-mode table that the supervisor reads at
startup. Soccer starts active (FIFA World Cup runway begins June 11 2026);
all other sports start passive so we still capture schedules and opening
lines without spending Kalshi/Odds API budget on paper trades.

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4a18bd69107"
down_revision: Union[str, Sequence[str], None] = "5af3e7d68c1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SPORTS = ("nhl", "nba", "mlb", "nfl", "soccer", "ufc")
ACTIVE_SPORTS = {"soccer"}


def upgrade() -> None:
    sport_configs = op.create_table(
        "sport_configs",
        sa.Column("sport", sa.String(length=20), primary_key=True),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.bulk_insert(
        sport_configs,
        [
            {
                "sport": sport,
                "mode": "active" if sport in ACTIVE_SPORTS else "passive",
                "notes": (
                    "Primary focus: 2026 FIFA World Cup (June 11 – July 19)."
                    if sport in ACTIVE_SPORTS
                    else "Schedule + opening lines only; flip to active when in-season."
                ),
            }
            for sport in SPORTS
        ],
    )


def downgrade() -> None:
    op.drop_table("sport_configs")
