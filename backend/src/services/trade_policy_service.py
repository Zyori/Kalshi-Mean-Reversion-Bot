from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.trade import PaperTrade


async def evaluate_trade_gate(
    db: AsyncSession,
    event: dict,
) -> str | None:
    if event.get("classification") != "reversion_candidate":
        return "not_reversion_candidate"

    market_id = event.get("market_id")
    if market_id is None:
        return "missing_market"

    confidence = float(event.get("confidence_score") or 0.0)
    if confidence < settings.paper_trade_min_confidence:
        return "confidence_below_threshold"

    deviation = float(event.get("deviation") or 0.0)
    if deviation < settings.paper_trade_min_deviation:
        return "deviation_below_threshold"

    open_trade = await db.scalar(
        select(PaperTrade.id).where(
            PaperTrade.market_id == market_id,
            PaperTrade.status == "open",
        )
    )
    if open_trade is not None:
        return "market_already_open"

    return None
