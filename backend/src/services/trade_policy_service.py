from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.trade import PaperTrade
from src.strategy.market_policy import get_trade_gate_settings


def _confidence_threshold(market_category: str | None) -> float:
    thresholds = get_trade_gate_settings()
    return thresholds.get(market_category or "", {}).get(
        "confidence",
        settings.paper_trade_min_confidence,
    )


def _deviation_threshold(market_category: str | None) -> float:
    thresholds = get_trade_gate_settings()
    return thresholds.get(market_category or "", {}).get(
        "deviation",
        settings.paper_trade_min_deviation,
    )


async def evaluate_trade_gate(
    db: AsyncSession,
    event: dict,
    trade: dict,
) -> str | None:
    if event.get("classification") != "reversion_candidate":
        return "not_reversion_candidate"

    market_id = event.get("market_id")
    if market_id is None:
        return "missing_market"

    market_category = trade.get("market_category") or event.get("market_category")
    confidence = float(event.get("confidence_score") or 0.0)
    if confidence < _confidence_threshold(market_category):
        return "confidence_below_threshold"

    deviation = float(event.get("deviation") or 0.0)
    if deviation < _deviation_threshold(market_category):
        return "deviation_below_threshold"

    game_event_id = event.get("game_event_id")
    if game_event_id is not None:
        event_trade = await db.scalar(
            select(PaperTrade.id).where(
                PaperTrade.market_id == market_id,
                PaperTrade.game_event_id == game_event_id,
            )
        )
        if event_trade is not None:
            return "event_already_traded"

    open_count = await db.scalar(
        select(func.count(PaperTrade.id)).where(
            PaperTrade.market_id == market_id,
            PaperTrade.status == "open",
        )
    )
    if (open_count or 0) >= settings.paper_trade_max_open_per_market:
        return "market_position_limit"

    latest_open_trade = await db.scalar(
        select(PaperTrade)
        .where(
            PaperTrade.market_id == market_id,
            PaperTrade.status == "open",
        )
        .order_by(PaperTrade.entered_at.desc(), PaperTrade.id.desc())
        .limit(1)
    )
    if latest_open_trade is not None:
        same_side = latest_open_trade.side == trade.get("side")
        entry_move = abs((trade.get("entry_price") or 0) - latest_open_trade.entry_price)
        if same_side and entry_move < settings.paper_trade_reentry_min_price_move_cents:
            return "market_state_unchanged"

    return None
