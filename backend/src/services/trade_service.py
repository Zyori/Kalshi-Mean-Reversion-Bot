from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.trade import PaperTrade

logger = get_logger(__name__)

ALLOWED_SORT_COLUMNS = {"entered_at", "sport", "status", "pnl_cents", "confidence_score"}
ALLOWED_FILTER_COLUMNS = {"sport", "status"}


async def get_trades(
    db: AsyncSession,
    sport: str | None = None,
    status: str | None = None,
    sort_by: str = "entered_at",
    limit: int = 50,
    offset: int = 0,
) -> Sequence[PaperTrade]:
    stmt = select(PaperTrade)

    if sport and "sport" in ALLOWED_FILTER_COLUMNS:
        stmt = stmt.where(PaperTrade.sport == sport)
    if status and "status" in ALLOWED_FILTER_COLUMNS:
        stmt = stmt.where(PaperTrade.status == status)

    if sort_by in ALLOWED_SORT_COLUMNS:
        stmt = stmt.order_by(getattr(PaperTrade, sort_by).desc())
    else:
        stmt = stmt.order_by(PaperTrade.entered_at.desc())

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_active_trades(db: AsyncSession) -> Sequence[PaperTrade]:
    stmt = (
        select(PaperTrade).where(PaperTrade.status == "open").order_by(PaperTrade.entered_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_trade_by_id(db: AsyncSession, trade_id: int) -> PaperTrade | None:
    stmt = select(PaperTrade).where(PaperTrade.id == trade_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
