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
                "game_event_id": 1,
                "confidence_score": 0.78,
                "deviation": 0.31,
            },
            {"side": "yes", "entry_price": 25},
        )
        assert reason is None


async def test_trade_gate_blocks_same_event_retrade(db_session_factory):
    async with db_session_factory() as db:
        market = await _seed_market(db)
        db.add(
            PaperTrade(
                game_event_id=1,
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
                "game_event_id": 1,
                "confidence_score": 0.78,
                "deviation": 0.31,
            },
            {"side": "yes", "entry_price": 25},
        )
        assert reason == "event_already_traded"


async def test_trade_gate_blocks_low_confidence(db_session_factory):
    async with db_session_factory() as db:
        market = await _seed_market(db)
        reason = await evaluate_trade_gate(
            db,
            {
                "classification": "reversion_candidate",
                "market_id": market.id,
                "game_event_id": 1,
                "confidence_score": 0.2,
                "deviation": 0.31,
            },
            {"side": "yes", "entry_price": 25},
        )
        assert reason == "confidence_below_threshold"


async def test_trade_gate_allows_ladder_when_market_moves(db_session_factory):
    async with db_session_factory() as db:
        market = await _seed_market(db)
        db.add(
            PaperTrade(
                game_event_id=1,
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
                "game_event_id": 2,
                "confidence_score": 0.78,
                "deviation": 0.31,
            },
            {"side": "yes", "entry_price": 18},
        )
        assert reason is None


async def test_trade_gate_blocks_unchanged_market_state(db_session_factory):
    async with db_session_factory() as db:
        market = await _seed_market(db)
        db.add(
            PaperTrade(
                game_event_id=1,
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
                "game_event_id": 2,
                "confidence_score": 0.78,
                "deviation": 0.31,
            },
            {"side": "yes", "entry_price": 22},
        )
        assert reason == "market_state_unchanged"


async def test_trade_gate_respects_open_trade_cap(db_session_factory):
    async with db_session_factory() as db:
        market = await _seed_market(db)
        for idx, entry in enumerate((25, 18, 10), start=1):
            db.add(
                PaperTrade(
                    game_event_id=idx,
                    market_id=market.id,
                    sport="mlb",
                    side="yes",
                    entry_price=entry,
                    entry_price_adj=min(99, entry + 1),
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
                "game_event_id": 4,
                "confidence_score": 0.78,
                "deviation": 0.31,
            },
            {"side": "yes", "entry_price": 4},
        )
        assert reason == "market_position_limit"
