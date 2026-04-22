"""add trade decision audit table

Revision ID: 5af3e7d68c1b
Revises: 37e71f7b5a29
Create Date: 2026-04-22 14:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5af3e7d68c1b"
down_revision: Union[str, Sequence[str], None] = "37e71f7b5a29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trade_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_event_id", sa.Integer(), nullable=True),
        sa.Column("market_id", sa.Integer(), nullable=True),
        sa.Column("sport", sa.String(length=20), nullable=False),
        sa.Column("market_category", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("deviation", sa.Float(), nullable=True),
        sa.Column("entry_price", sa.Integer(), nullable=True),
        sa.Column("skip_reason", sa.String(length=200), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "entered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["game_event_id"], ["game_events.id"]),
        sa.ForeignKeyConstraint(["market_id"], ["markets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("trade_decisions", schema=None) as batch_op:
        batch_op.create_index("ix_trade_decisions_action", ["action"], unique=False)
        batch_op.create_index("ix_trade_decisions_entered_at", ["entered_at"], unique=False)
        batch_op.create_index(
            "ix_trade_decisions_market_category",
            ["market_category"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("trade_decisions", schema=None) as batch_op:
        batch_op.drop_index("ix_trade_decisions_market_category")
        batch_op.drop_index("ix_trade_decisions_entered_at")
        batch_op.drop_index("ix_trade_decisions_action")

    op.drop_table("trade_decisions")
