"""Contract tests for the trade-reconciliation safety net."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.database import Base, create_engine
from src.models.game import Game
from src.models.market import Market
from src.models.trade import PaperTrade
from src.paper_trader.portfolio import Portfolio
from src.paper_trader.simulator import PaperTradeSimulator
from src.services.trade_reconciliation import reconcile_open_trades


@pytest.fixture
async def db_session_factory():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


def _simulator() -> PaperTradeSimulator:
    return PaperTradeSimulator(Portfolio())


async def _seed_game_with_trade(
    db,
    *,
    sport: str = "soccer",
    home_team: str = "Celta Vigo",
    away_team: str = "Levante",
    status: str,
    latest_home: int | None,
    latest_away: int | None,
    final_home: int | None = None,
    final_away: int | None = None,
    side: str = "yes",
    entry: int = 71,
) -> PaperTrade:
    game = Game(
        sport=sport,
        home_team=home_team,
        away_team=away_team,
        start_time=datetime(2026, 5, 12, 17, tzinfo=UTC),
        status=status,
        latest_home_score=latest_home,
        latest_away_score=latest_away,
        final_home_score=final_home,
        final_away_score=final_away,
    )
    db.add(game)
    await db.flush()
    market = Market(
        game_id=game.id,
        kalshi_ticker="KX-TEST-MARKET",
        market_type="kalshi_game_winner_demo",
    )
    db.add(market)
    await db.flush()
    trade = PaperTrade(
        market_id=market.id,
        sport=sport,
        market_category="moneyline",
        side=side,
        entry_price=entry,
        entry_price_adj=entry,
        slippage_cents=0,
        confidence_score=0.5,
        kelly_fraction=0.0,
        kelly_size_cents=100,
        status="open",
        game_context="{}",
    )
    db.add(trade)
    await db.commit()
    return trade


async def test_resolves_soccer_full_time_with_missing_final_score(db_session_factory):
    # The original bug: soccer games ended STATUS_FULL_TIME but
    # final_home_score stayed NULL because the old ingestion only knew
    # about STATUS_FINAL / "post". Reconciliation should backfill from
    # latest_*_score and resolve the trade.
    async with db_session_factory() as db:
        await _seed_game_with_trade(
            db,
            status="STATUS_FULL_TIME",
            latest_home=2,
            latest_away=0,
            final_home=None,
            final_away=None,
            side="yes",
            entry=60,
        )
        count = await reconcile_open_trades(db, _simulator())
        assert count == 1
        result = await db.execute(select(PaperTrade))
        trade = result.scalar_one()
        assert trade.status == "resolved_win"
        assert trade.resolution == "yes"


async def test_skips_games_still_in_progress(db_session_factory):
    async with db_session_factory() as db:
        await _seed_game_with_trade(
            db,
            status="STATUS_SECOND_HALF",
            latest_home=1,
            latest_away=1,
        )
        count = await reconcile_open_trades(db, _simulator())
        assert count == 0
        result = await db.execute(select(PaperTrade))
        trade = result.scalar_one()
        assert trade.status == "open"


async def test_resolves_us_sport_status_final(db_session_factory):
    async with db_session_factory() as db:
        await _seed_game_with_trade(
            db,
            sport="nba",
            home_team="Lakers",
            away_team="Celtics",
            status="STATUS_FINAL",
            latest_home=108,
            latest_away=112,
            side="no",  # Bet the away team
            entry=50,
        )
        count = await reconcile_open_trades(db, _simulator())
        assert count == 1
        result = await db.execute(select(PaperTrade))
        trade = result.scalar_one()
        assert trade.status == "resolved_win"


async def test_handles_final_pen_status(db_session_factory):
    async with db_session_factory() as db:
        await _seed_game_with_trade(
            db,
            status="STATUS_FINAL_PEN",
            latest_home=3,
            latest_away=2,
            side="yes",
            entry=55,
        )
        count = await reconcile_open_trades(db, _simulator())
        assert count == 1
