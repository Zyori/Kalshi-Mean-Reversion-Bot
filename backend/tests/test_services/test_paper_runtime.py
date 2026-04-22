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
from src.services.paper_runtime import (
    attach_synthetic_market_contexts,
    resolve_game_trades,
    restore_portfolio_state,
)


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
            opening_home_team_total=112.5,
            opening_away_team_total=109.0,
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

        categories = [payload["market_category"] for payload in payloads]
        assert categories.count("team_total") == 2
        assert set(categories) == {"moneyline", "spread", "total", "team_total"}
        total_payload = next(
            payload
            for payload in payloads
            if payload["market_category"] == "total"
        )
        assert total_payload["market_label_yes"] == "Over 221.5"
        assert total_payload["market_label_no"] == "Under 221.5"
        team_total_payload = next(
            payload
            for payload in payloads
            if payload["market_category"] == "team_total" and payload["team_total_side"] == "home"
        )
        assert team_total_payload["market_label_yes"] == "Boston Celtics Over 112.5"
        assert team_total_payload["market_label_no"] == "Boston Celtics Under 112.5"


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


async def test_restore_portfolio_state_uses_db_bankroll_and_open_positions(db_session_factory):
    async with db_session_factory() as db:
        db.add_all(
            [
                PaperTrade(
                    market_id=1,
                    sport="mlb",
                    market_category="moneyline",
                    side="yes",
                    entry_price=40,
                    entry_price_adj=41,
                    slippage_cents=1,
                    kelly_size_cents=2500,
                    status="open",
                    pnl_cents=None,
                ),
                PaperTrade(
                    market_id=2,
                    sport="mlb",
                    market_category="spread",
                    side="no",
                    entry_price=35,
                    entry_price_adj=36,
                    slippage_cents=1,
                    kelly_size_cents=1500,
                    status="resolved_win",
                    pnl_cents=2200,
                ),
            ]
        )
        await db.commit()

        portfolio = Portfolio(initial_bankroll_cents=100000)
        await restore_portfolio_state(db, portfolio)

        assert portfolio.bankroll_cents == 102200
        assert portfolio.open_count == 1
        assert portfolio.pending_wagers_cents == 2500


async def test_resolve_game_trades_settles_team_total_markets(db_session_factory):
    async with db_session_factory() as db:
        game = Game(
            sport="nba",
            home_team="Boston Celtics",
            away_team="New York Knicks",
            start_time=datetime(2026, 4, 22, 23, 0, tzinfo=UTC),
            status="STATUS_FINAL",
            final_home_score=118,
            final_away_score=104,
            opening_home_team_total=112.5,
            opening_away_team_total=108.5,
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
                "home_score": 60,
                "away_score": 48,
                "period": "3",
            },
            include_moneyline=False,
        )

        home_team_total = next(
            item
            for item in payloads
            if item["market_category"] == "team_total" and item["team_total_side"] == "home"
        )
        away_team_total = next(
            item
            for item in payloads
            if item["market_category"] == "team_total" and item["team_total_side"] == "away"
        )

        db.add_all(
            [
                PaperTrade(
                    market_id=home_team_total["market_id"],
                    sport="nba",
                    market_category="team_total",
                    side="yes",
                    entry_price=43,
                    entry_price_adj=44,
                    slippage_cents=1,
                    kelly_size_cents=2500,
                    status="open",
                    game_context=json.dumps(home_team_total),
                ),
                PaperTrade(
                    market_id=away_team_total["market_id"],
                    sport="nba",
                    market_category="team_total",
                    side="yes",
                    entry_price=41,
                    entry_price_adj=42,
                    slippage_cents=1,
                    kelly_size_cents=2500,
                    status="open",
                    game_context=json.dumps(away_team_total),
                ),
            ]
        )
        await db.commit()

        simulator = PaperTradeSimulator(Portfolio(initial_bankroll_cents=100000))
        resolved = await resolve_game_trades(db, simulator, game)
        await db.commit()

        statuses = sorted(trade.status for trade in resolved)
        assert statuses == ["resolved_loss", "resolved_win"]
