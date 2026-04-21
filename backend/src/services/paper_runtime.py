import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.game import Game
from src.models.market import Market, MarketSnapshot
from src.models.trade import PaperTrade
from src.paper_trader.simulator import PaperTradeSimulator

logger = get_logger(__name__)

SYNTHETIC_MARKET_TYPE = "synthetic_home_win"
SYNTHETIC_TICKER_PREFIX = "SYN-HOMEWIN"

SCORE_IMPACT_WEIGHTS: dict[str, float] = {
    "nhl": 0.16,
    "nba": 0.018,
    "mlb": 0.14,
    "nfl": 0.032,
    "soccer": 0.20,
    "ufc": 0.10,
}


def _clamp_probability(value: float) -> float:
    return max(0.05, min(0.95, value))


def _score_margin_shift(game: Game, event: dict[str, Any]) -> float:
    home_score = int(event.get("home_score") or 0)
    away_score = int(event.get("away_score") or 0)
    margin = home_score - away_score
    weight = SCORE_IMPACT_WEIGHTS.get(game.sport, 0.05)
    time_factor = _time_factor(game.sport, event.get("period"))
    return margin * weight * time_factor


def _time_factor(sport: str, period: str | None) -> float:
    try:
        current = int(period or 0)
    except (TypeError, ValueError):
        current = 0

    totals = {
        "nhl": 3,
        "nba": 4,
        "mlb": 9,
        "nfl": 4,
        "soccer": 2,
        "ufc": 3,
    }
    total = totals.get(sport, 4)
    elapsed = min(max(current / max(total, 1), 0.0), 1.0)
    return 0.35 + elapsed * 0.9


def estimate_synthetic_home_price(game: Game, event: dict[str, Any]) -> int:
    baseline = game.opening_line_home_prob or 0.5
    price = _clamp_probability(baseline + _score_margin_shift(game, event))
    return round(price * 100)


async def get_game_by_espn_id(db: AsyncSession, espn_id: str) -> Game | None:
    result = await db.execute(select(Game).where(Game.espn_id == espn_id))
    return result.scalar_one_or_none()


async def ensure_synthetic_market(db: AsyncSession, game: Game) -> Market:
    ticker = f"{SYNTHETIC_TICKER_PREFIX}-{game.id}"
    result = await db.execute(select(Market).where(Market.kalshi_ticker == ticker))
    market = result.scalar_one_or_none()
    if market is None:
        market = Market(
            game_id=game.id,
            kalshi_ticker=ticker,
            market_type=SYNTHETIC_MARKET_TYPE,
            opened_at=datetime.now(UTC),
        )
        db.add(market)
        await db.flush()
    return market


async def attach_synthetic_market_context(
    db: AsyncSession,
    game: Game,
    event: dict[str, Any],
) -> dict[str, Any]:
    market = await ensure_synthetic_market(db, game)
    yes_price = estimate_synthetic_home_price(game, event)
    event["market_id"] = market.id
    event["market_type"] = market.market_type
    event["kalshi_price_at"] = yes_price
    event["fair_prob_yes"] = game.opening_line_home_prob or 0.5
    event["ask_depth"] = 25

    snapshot = MarketSnapshot(
        market_id=market.id,
        kalshi_bid=max(1, yes_price - 2),
        kalshi_ask=min(99, yes_price + 2),
        kalshi_volume=None,
        bid_depth=25,
        ask_depth=25,
    )
    db.add(snapshot)
    await db.flush()
    return event


async def persist_trade(
    db: AsyncSession,
    trade: dict[str, Any],
    *,
    game_event_id: int | None,
) -> PaperTrade:
    record = PaperTrade(
        game_event_id=game_event_id,
        market_id=trade["market_id"],
        sport=trade["sport"],
        side=trade["side"],
        entry_price=trade["entry_price"],
        entry_price_adj=trade["entry_price_adj"],
        slippage_cents=trade["slippage_cents"],
        confidence_score=trade.get("confidence_score"),
        kelly_fraction=trade.get("kelly_fraction"),
        kelly_size_cents=trade.get("kelly_size_cents"),
        status=trade["status"],
        game_context=json.dumps(trade.get("game_context", {})),
        reasoning=trade.get("reasoning"),
    )
    db.add(record)
    await db.flush()
    trade["db_id"] = record.id
    return record


async def load_open_trades(db: AsyncSession) -> list[PaperTrade]:
    result = await db.execute(select(PaperTrade).where(PaperTrade.status == "open"))
    return result.scalars().all()


async def resolve_game_trades(
    db: AsyncSession,
    simulator: PaperTradeSimulator,
    game: Game,
) -> list[PaperTrade]:
    result = await db.execute(
        select(PaperTrade)
        .join(Market, PaperTrade.market_id == Market.id)
        .where(Market.game_id == game.id, PaperTrade.status == "open")
    )
    open_trades = result.scalars().all()
    if not open_trades:
        return []

    resolved_records: list[PaperTrade] = []
    final_home = getattr(game, "final_home_score", None)
    final_away = getattr(game, "final_away_score", None)
    if final_home is None or final_away is None:
        logger.warning("resolve_missing_final_score", game_id=game.id)
        return []

    home_wins = final_home > final_away
    for trade in open_trades:
        trade_payload = {
            "id": trade.id,
            "entry_price_adj": trade.entry_price_adj,
            "kelly_size_cents": trade.kelly_size_cents or 0,
            "flat_size_cents": 500,
            "side": trade.side,
        }
        won = home_wins if trade.side == "yes" else not home_wins
        resolved = simulator.resolve_trade(trade_payload, exit_price=100 if won else 0, won=won)
        trade.exit_price = resolved["exit_price"]
        trade.pnl_cents = resolved["pnl_cents"]
        trade.pnl_kelly_cents = resolved["pnl_kelly_cents"]
        trade.status = resolved["status"]
        trade.resolved_at = datetime.now(UTC)
        trade.resolution = resolved["resolution"]
        resolved_records.append(trade)
    await db.flush()
    return resolved_records
