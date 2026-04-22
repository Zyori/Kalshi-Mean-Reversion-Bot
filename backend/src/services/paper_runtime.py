import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.logging import get_logger
from src.models.game import Game
from src.models.market import Market, MarketSnapshot
from src.models.trade import PaperTrade
from src.paper_trader.portfolio import Portfolio
from src.paper_trader.simulator import PaperTradeSimulator

logger = get_logger(__name__)

SYNTHETIC_MARKETS: dict[str, dict[str, str]] = {
    "moneyline": {
        "market_type": "synthetic_home_win",
        "ticker_prefix": "SYN-HOMEWIN",
    },
    "spread": {
        "market_type": "synthetic_home_spread",
        "ticker_prefix": "SYN-HOMESPREAD",
    },
    "total": {
        "market_type": "synthetic_total_over",
        "ticker_prefix": "SYN-TOTALOVER",
    },
}

SCORE_IMPACT_WEIGHTS: dict[str, float] = {
    "nhl": 0.16,
    "nba": 0.018,
    "mlb": 0.14,
    "nfl": 0.032,
    "soccer": 0.20,
    "ufc": 0.10,
}

SPREAD_IMPACT_WEIGHTS: dict[str, float] = {
    "nhl": 0.10,
    "nba": 0.035,
    "mlb": 0.10,
    "nfl": 0.05,
    "soccer": 0.14,
    "ufc": 0.08,
}

TOTAL_IMPACT_WEIGHTS: dict[str, float] = {
    "nhl": 0.08,
    "nba": 0.012,
    "mlb": 0.07,
    "nfl": 0.02,
    "soccer": 0.12,
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


def _game_progress(sport: str, period: str | None) -> float:
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
    return min(max(current / max(total, 1), 0.0), 1.0)


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


def estimate_synthetic_spread_price(game: Game, event: dict[str, Any]) -> int | None:
    if game.opening_spread_home is None:
        return None

    home_score = int(event.get("home_score") or 0)
    away_score = int(event.get("away_score") or 0)
    cover_edge = (home_score - away_score) + float(game.opening_spread_home)
    time_factor = _time_factor(game.sport, event.get("period"))
    weight = SPREAD_IMPACT_WEIGHTS.get(game.sport, 0.04)
    price = _clamp_probability(0.5 + cover_edge * weight * time_factor)
    return round(price * 100)


def estimate_synthetic_total_price(game: Game, event: dict[str, Any]) -> int | None:
    if game.opening_total is None:
        return None

    home_score = int(event.get("home_score") or 0)
    away_score = int(event.get("away_score") or 0)
    progress = _game_progress(game.sport, event.get("period"))
    if progress <= 0:
        return 50

    projected_total = (home_score + away_score) / max(progress, 0.15)
    total_edge = projected_total - float(game.opening_total)
    weight = TOTAL_IMPACT_WEIGHTS.get(game.sport, 0.02)
    price = _clamp_probability(0.5 + total_edge * weight * max(progress, 0.25))
    return round(price * 100)


async def get_game_by_espn_id(db: AsyncSession, espn_id: str) -> Game | None:
    result = await db.execute(select(Game).where(Game.espn_id == espn_id))
    return result.scalar_one_or_none()


def _market_spec(market_category: str) -> dict[str, str]:
    return SYNTHETIC_MARKETS.get(market_category, SYNTHETIC_MARKETS["moneyline"])


async def ensure_synthetic_market(
    db: AsyncSession,
    game: Game,
    market_category: str,
) -> Market:
    spec = _market_spec(market_category)
    ticker = f"{spec['ticker_prefix']}-{game.id}"
    result = await db.execute(select(Market).where(Market.kalshi_ticker == ticker))
    market = result.scalar_one_or_none()
    if market is None:
        market = Market(
            game_id=game.id,
            kalshi_ticker=ticker,
            market_type=spec["market_type"],
            opened_at=datetime.now(UTC),
        )
        db.add(market)
        await db.flush()
    return market


def _market_labels(game: Game, market_category: str) -> tuple[str, str]:
    if market_category == "spread":
        home_line = game.opening_spread_home
        away_line = game.opening_spread_away
        return (
            f"{game.home_team} {home_line:+.1f}" if home_line is not None else game.home_team,
            f"{game.away_team} {away_line:+.1f}" if away_line is not None else game.away_team,
        )
    if market_category == "total":
        total = game.opening_total
        total_text = f"{total:.1f}" if total is not None else "--"
        return (f"Over {total_text}", f"Under {total_text}")
    return (game.home_team, game.away_team)


async def attach_synthetic_market_context(
    db: AsyncSession,
    game: Game,
    event: dict[str, Any],
    *,
    market_category: str = "moneyline",
) -> dict[str, Any]:
    market = await ensure_synthetic_market(db, game, market_category)
    if market_category == "spread":
        yes_price = estimate_synthetic_spread_price(game, event)
        fair_prob_yes = 0.5
    elif market_category == "total":
        yes_price = estimate_synthetic_total_price(game, event)
        fair_prob_yes = 0.5
    else:
        yes_price = estimate_synthetic_home_price(game, event)
        fair_prob_yes = game.opening_line_home_prob or 0.5

    if yes_price is None:
        return event

    yes_label, no_label = _market_labels(game, market_category)
    event["market_id"] = market.id
    event["market_type"] = market.market_type
    event["market_category"] = market_category
    event["market_source"] = "synthetic"
    event["kalshi_price_at"] = yes_price
    event["kalshi_yes_ask"] = yes_price
    event["kalshi_no_ask"] = 100 - yes_price
    event["kalshi_yes_ask_depth"] = 25
    event["kalshi_no_ask_depth"] = 25
    event["fair_prob_yes"] = fair_prob_yes
    event["baseline_prob"] = fair_prob_yes
    event["market_label_yes"] = yes_label
    event["market_label_no"] = no_label
    event["opening_spread_home"] = game.opening_spread_home
    event["opening_spread_away"] = game.opening_spread_away
    event["opening_total"] = game.opening_total
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


async def attach_synthetic_market_contexts(
    db: AsyncSession,
    game: Game,
    event: dict[str, Any],
    *,
    include_moneyline: bool,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    categories: list[str] = []
    if include_moneyline:
        categories.append("moneyline")
    if game.opening_spread_home is not None:
        categories.append("spread")
    if game.opening_total is not None:
        categories.append("total")

    for market_category in categories:
        payload = dict(event)
        enriched = await attach_synthetic_market_context(
            db,
            game,
            payload,
            market_category=market_category,
        )
        if enriched.get("market_id") is not None:
            payloads.append(enriched)
    return payloads


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
        market_category=trade.get("market_category", "moneyline"),
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


async def restore_portfolio_state(
    db: AsyncSession,
    portfolio: Portfolio,
) -> None:
    total_pnl = await db.scalar(
        select(func.sum(PaperTrade.pnl_cents)).where(PaperTrade.status != "open")
    )
    bankroll_cents = settings.paper_bankroll_start_cents + int(total_pnl or 0)
    open_trades = await load_open_trades(db)
    open_positions = {
        trade.id: int(trade.kelly_size_cents or 0)
        for trade in open_trades
    }
    portfolio.sync_state(
        bankroll_cents=bankroll_cents,
        open_positions=open_positions,
    )


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
    total_points = final_home + final_away
    for trade in open_trades:
        context = json.loads(trade.game_context) if trade.game_context else {}
        trade_payload = {
            "id": trade.id,
            "entry_price_adj": trade.entry_price_adj,
            "kelly_size_cents": trade.kelly_size_cents or 0,
            "flat_size_cents": 500,
            "side": trade.side,
        }
        push = False

        if trade.market_category == "spread":
            home_spread = context.get("opening_spread_home", game.opening_spread_home)
            if home_spread is None:
                continue
            cover_margin = final_home + float(home_spread) - final_away
            if abs(cover_margin) < 1e-9:
                push = True
                won = False
            else:
                yes_wins = cover_margin > 0
                won = yes_wins if trade.side == "yes" else not yes_wins
        elif trade.market_category == "total":
            total_line = context.get("opening_total", game.opening_total)
            if total_line is None:
                continue
            if abs(total_points - float(total_line)) < 1e-9:
                push = True
                won = False
            else:
                yes_wins = total_points > float(total_line)
                won = yes_wins if trade.side == "yes" else not yes_wins
        else:
            won = home_wins if trade.side == "yes" else not home_wins

        resolved = simulator.resolve_trade(
            trade_payload,
            exit_price=trade.entry_price_adj if push else (100 if won else 0),
            won=won,
            push=push,
        )
        trade.exit_price = resolved["exit_price"]
        trade.pnl_cents = resolved["pnl_cents"]
        trade.pnl_kelly_cents = resolved["pnl_kelly_cents"]
        trade.status = resolved["status"]
        trade.resolved_at = datetime.now(UTC)
        trade.resolution = resolved["resolution"]
        resolved_records.append(trade)
    await db.flush()
    return resolved_records
