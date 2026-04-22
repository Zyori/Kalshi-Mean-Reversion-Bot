from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.database import Base, create_engine
from src.models.game import Game, GameEvent
from src.models.market import Market
from src.models.trade import PaperTrade
from src.services.trade_policy_service import evaluate_trade_gate


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


async def _seed_market(db) -> Market:
    game = Game(
        sport="mlb",
        home_team="Miami Marlins",
        away_team="St. Louis Cardinals",
        start_time=datetime(2026, 4, 21, 23, 0, tzinfo=UTC),
        espn_id="401999888",
        status="STATUS_IN_PROGRESS",
    )
    db.add(game)
    await db.flush()

    event = GameEvent(
        game_id=game.id,
        event_type="Home Run",
        description="Pitch 3 : Ball In Play",
        detected_at=datetime(2026, 4, 21, 23, 42, tzinfo=UTC),
    )
    db.add(event)
    await db.flush()

    market = Market(
        game_id=game.id,
        kalshi_ticker="SYN-HOMEWIN-1",
        market_type="synthetic_home_win",
        opened_at=datetime(2026, 4, 21, 23, 40, tzinfo=UTC),
    )
    db.add(market)
    await db.flush()
    return market


async def test_trade_gate_allows_clean_candidate(db_session_factory):
    async with db_session_factory() as db:
        market = await _seed_market(db)
        reason = await evaluate_trade_gate(
            db,
            {
                "classification": "reversion_candidate",
                "market_id": market.id,
                "confidence_score": 0.78,
                "deviation": 0.31,
            },
        )
        assert reason is None


async def test_trade_gate_blocks_duplicate_open_market(db_session_factory):
    async with db_session_factory() as db:
        market = await _seed_market(db)
        db.add(
            PaperTrade(
                market_id=market.id,
                sport="mlb",
                side="yes",
                entry_price=25,
                entry_price_adj=26,
                slippage_cents=1,
                status="open",
            )
        )
        await db.flush()

        reason = await evaluate_trade_gate(
            db,
            {
                "classification": "reversion_candidate",
                "market_id": market.id,
                "confidence_score": 0.78,
                "deviation": 0.31,
            },
        )
        assert reason == "market_already_open"


async def test_trade_gate_blocks_low_confidence(db_session_factory):
    async with db_session_factory() as db:
        market = await _seed_market(db)
        reason = await evaluate_trade_gate(
            db,
            {
                "classification": "reversion_candidate",
                "market_id": market.id,
                "confidence_score": 0.2,
                "deviation": 0.31,
            },
        )
        assert reason == "confidence_below_threshold"
