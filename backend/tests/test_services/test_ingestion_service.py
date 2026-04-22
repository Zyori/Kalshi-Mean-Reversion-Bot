from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.database import Base, create_engine
from src.models import Game, GameEvent, OpeningLine
from src.services.ingestion_service import (
    record_game_event,
    record_opening_line,
    upsert_game_from_scoreboard,
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


async def test_record_opening_line_creates_game_and_line(db_session_factory):
    async with db_session_factory() as db:
        game = await record_opening_line(
            db,
            {
                "sport": "nhl",
                "home_team": "Edmonton Oilers",
                "away_team": "Calgary Flames",
                "start_time": "2026-04-21T19:00:00Z",
                "source": "draftkings",
                "home_prob": 0.57,
                "away_prob": 0.43,
                "home_spread": -1.5,
                "away_spread": 1.5,
                "total_points": 6.5,
                "home_team_total": 3.5,
                "away_team_total": 2.5,
                "captured_at": "2026-04-21T10:00:00Z",
                "odds_raw": {
                    "h2h": {"home": -133, "away": 120},
                    "spreads": {
                        "home": {"point": -1.5, "price": -110},
                        "away": {"point": 1.5, "price": -110},
                    },
                    "totals": {
                        "over": {"point": 6.5, "price": -110},
                        "under": {"point": 6.5, "price": -110},
                    },
                    "team_totals": {
                        "home": [{"point": 3.5, "price": -110, "name": "Over"}],
                        "away": [{"point": 2.5, "price": -110, "name": "Over"}],
                    },
                },
            },
        )
        await db.commit()

        assert game.id is not None

        stored_game = await db.get(Game, game.id)
        assert stored_game is not None
        assert stored_game.opening_line_home_prob == 0.57
        assert stored_game.opening_spread_home == pytest.approx(-1.5)
        assert stored_game.opening_total == pytest.approx(6.5)
        assert stored_game.opening_home_team_total == pytest.approx(3.5)
        assert stored_game.opening_away_team_total == pytest.approx(2.5)

        lines = (await db.execute(OpeningLine.__table__.select())).all()
        assert len(lines) == 1
        line = lines[0]
        assert line.home_spread == pytest.approx(-1.5)
        assert line.total_points == pytest.approx(6.5)
        assert line.home_team_total == pytest.approx(3.5)
        assert line.away_team_total == pytest.approx(2.5)


async def test_upsert_scoreboard_matches_existing_game_by_teams_and_start_time(db_session_factory):
    async with db_session_factory() as db:
        existing = Game(
            sport="nba",
            home_team="Boston Celtics",
            away_team="New York Knicks",
            start_time=datetime(2026, 4, 21, 23, 0, tzinfo=UTC),
            status="scheduled",
        )
        db.add(existing)
        await db.flush()

        updated = await upsert_game_from_scoreboard(
            db,
            {
                "espn_id": "401999001",
                "sport": "nba",
                "home_team": "Boston Celtics",
                "away_team": "New York Knicks",
                "start_time": "2026-04-21T23:05:00Z",
                "status": "STATUS_IN_PROGRESS",
            },
        )
        await db.commit()

        assert updated.id == existing.id
        assert updated.espn_id == "401999001"
        assert updated.status == "STATUS_IN_PROGRESS"


async def test_record_game_event_attaches_to_game(db_session_factory):
    async with db_session_factory() as db:
        game = Game(
            sport="nhl",
            home_team="Dallas Stars",
            away_team="Colorado Avalanche",
            start_time=datetime(2026, 4, 21, 1, 0, tzinfo=UTC),
            espn_id="401999777",
            status="STATUS_IN_PROGRESS",
        )
        db.add(game)
        await db.flush()

        event = await record_game_event(
            db,
            {
                "espn_id": "401999777",
                "sport": "nhl",
                "event_type": "Goal",
                "description": "Dallas scores on the power play",
                "home_score": 2,
                "away_score": 1,
                "period": "2",
                "clock": "13:05",
                "detected_at": "2026-04-21T01:45:00Z",
                "classification": "reversion_candidate",
                "confidence_score": 0.71,
                "baseline_prob": 0.56,
                "deviation": 0.14,
            },
        )
        await db.commit()

        assert event is not None
        stored_event = await db.get(GameEvent, event.id)
        assert stored_event is not None
        assert stored_event.game_id == game.id
        assert stored_event.classification == "reversion_candidate"


async def test_record_opening_line_handles_naive_datetime_from_existing_sqlite_row(
    db_session_factory,
):
    async with db_session_factory() as db:
        existing = Game(
            sport="mlb",
            home_team="Los Angeles Dodgers",
            away_team="San Diego Padres",
            start_time=datetime(2026, 4, 22, 2, 10),
            status="scheduled",
        )
        db.add(existing)
        await db.flush()

        game = await record_opening_line(
            db,
            {
                "sport": "mlb",
                "home_team": "Los Angeles Dodgers",
                "away_team": "San Diego Padres",
                "start_time": "2026-04-22T02:10:00Z",
                "source": "draftkings",
                "home_prob": 0.61,
                "away_prob": 0.39,
                "home_spread": -1.5,
                "away_spread": 1.5,
                "total_points": 8.5,
                "home_team_total": 5.0,
                "away_team_total": 3.5,
                "captured_at": "2026-04-21T20:00:00Z",
                "odds_raw": {
                    "h2h": {"home": -156, "away": 140},
                    "spreads": {
                        "home": {"point": -1.5, "price": -110},
                        "away": {"point": 1.5, "price": -110},
                    },
                    "totals": {
                        "over": {"point": 8.5, "price": -110},
                        "under": {"point": 8.5, "price": -110},
                    },
                    "team_totals": {
                        "home": [{"point": 5.0, "price": -110, "name": "Over"}],
                        "away": [{"point": 3.5, "price": -110, "name": "Over"}],
                    },
                },
            },
        )
        await db.commit()

        assert game.id == existing.id
        refreshed = await db.get(Game, existing.id)
        assert refreshed is not None
        assert refreshed.opening_total == pytest.approx(8.5)
