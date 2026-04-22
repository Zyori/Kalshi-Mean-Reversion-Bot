import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.database import Base, create_engine
from src.models.game import Game
from src.models.trade import PaperTrade
from src.paper_trader.portfolio import Portfolio
from src.paper_trader.simulator import PaperTradeSimulator
from src.services.paper_runtime import attach_synthetic_market_contexts, resolve_game_trades


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


async def test_attach_synthetic_market_contexts_builds_multiple_market_views(db_session_factory):
    async with db_session_factory() as db:
        game = Game(
            sport="nba",
            home_team="Boston Celtics",
            away_team="New York Knicks",
            start_time=datetime(2026, 4, 22, 23, 0, tzinfo=UTC),
            opening_line_home_prob=0.62,
            opening_spread_home=-4.5,
            opening_spread_away=4.5,
            opening_total=221.5,
        )
        db.add(game)
        await db.flush()

        payloads = await attach_synthetic_market_contexts(
            db,
            game,
            {
                "sport": "nba",
                "espn_id": "401000001",
                "event_type": "Timeout",
                "home_score": 48,
                "away_score": 56,
                "period": "2",
            },
            include_moneyline=True,
        )

        categories = {payload["market_category"] for payload in payloads}
        assert categories == {"moneyline", "spread", "total"}
        total_payload = next(
            payload
            for payload in payloads
            if payload["market_category"] == "total"
        )
        assert total_payload["market_label_yes"] == "Over 221.5"
        assert total_payload["market_label_no"] == "Under 221.5"


async def test_resolve_game_trades_settles_spread_total_and_pushes(db_session_factory):
    async with db_session_factory() as db:
        game = Game(
            sport="nba",
            home_team="Boston Celtics",
            away_team="New York Knicks",
            start_time=datetime(2026, 4, 22, 23, 0, tzinfo=UTC),
            status="STATUS_FINAL",
            final_home_score=110,
            final_away_score=104,
            opening_spread_home=-6.0,
            opening_spread_away=6.0,
            opening_total=214.0,
        )
        db.add(game)
        await db.flush()

        spread_market, total_market = (
            await attach_synthetic_market_contexts(
                db,
                game,
                {
                    "sport": "nba",
                    "espn_id": "401000001",
                    "event_type": "Timeout",
                    "home_score": 52,
                    "away_score": 59,
                    "period": "2",
                },
                include_moneyline=False,
            )
        )

        spread_payload = next(
            item
            for item in (spread_market, total_market)
            if item["market_category"] == "spread"
        )
        total_payload = next(
            item
            for item in (spread_market, total_market)
            if item["market_category"] == "total"
        )

        db.add_all(
            [
                PaperTrade(
                    market_id=spread_payload["market_id"],
                    sport="nba",
                    market_category="spread",
                    side="yes",
                    entry_price=40,
                    entry_price_adj=41,
                    slippage_cents=1,
                    kelly_size_cents=2500,
                    status="open",
                    game_context=json.dumps(spread_payload),
                ),
                PaperTrade(
                    market_id=total_payload["market_id"],
                    sport="nba",
                    market_category="total",
                    side="no",
                    entry_price=38,
                    entry_price_adj=39,
                    slippage_cents=1,
                    kelly_size_cents=2500,
                    status="open",
                    game_context=json.dumps({**total_payload, "opening_total": 212.0}),
                ),
                PaperTrade(
                    market_id=total_payload["market_id"],
                    sport="nba",
                    market_category="total",
                    side="yes",
                    entry_price=44,
                    entry_price_adj=45,
                    slippage_cents=1,
                    kelly_size_cents=2500,
                    status="open",
                    game_context=json.dumps({**total_payload, "opening_total": 213.0}),
                ),
            ]
        )
        await db.commit()

        simulator = PaperTradeSimulator(Portfolio(initial_bankroll_cents=100000))
        resolved = await resolve_game_trades(db, simulator, game)
        await db.commit()

        statuses = sorted(trade.status for trade in resolved)
        assert statuses == ["resolved_loss", "resolved_push", "resolved_win"]

        result = await db.execute(select(PaperTrade).order_by(PaperTrade.id))
        trades = result.scalars().all()
        assert trades[0].status == "resolved_push"
        assert trades[0].pnl_cents == 0
        assert trades[1].status == "resolved_loss"
        assert trades[2].status == "resolved_win"
