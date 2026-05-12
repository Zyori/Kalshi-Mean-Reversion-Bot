"""add signal_kind to paper_trades

Revision ID: a3f7b4b97b83
Revises: 35c33759bcb8
Create Date: 2026-05-12 19:06:24.320739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f7b4b97b83'
down_revision: Union[str, Sequence[str], None] = '35c33759bcb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "paper_trades",
        sa.Column("signal_kind", sa.String(length=60), nullable=True),
    )
    op.create_index(
        "ix_paper_trades_signal_kind", "paper_trades", ["signal_kind"]
    )


def downgrade() -> None:
    op.drop_index("ix_paper_trades_signal_kind", table_name="paper_trades")
    op.drop_column("paper_trades", "signal_kind")
