from sqlalchemy.ext.asyncio import AsyncSession

from src.models.decision import TradeDecision


async def record_trade_decision(
    db: AsyncSession,
    *,
    event: dict,
    trade: dict | None,
    action: str,
    skip_reason: str | None = None,
    summary: str | None = None,
) -> TradeDecision:
    decision = TradeDecision(
        game_event_id=event.get("game_event_id"),
        market_id=event.get("market_id"),
        sport=event.get("sport", ""),
        market_category=(trade or {}).get(
            "market_category",
            event.get("market_category", "moneyline"),
        ),
        action=action,
        side=(trade or {}).get("side"),
        confidence_score=event.get("confidence_score"),
        deviation=event.get("deviation"),
        entry_price=(trade or {}).get("entry_price"),
        skip_reason=skip_reason,
        summary=summary,
    )
    db.add(decision)
    await db.flush()
    return decision
