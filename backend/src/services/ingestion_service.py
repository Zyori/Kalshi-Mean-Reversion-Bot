import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.game import Game, GameEvent
from src.models.market import OpeningLine

logger = get_logger(__name__)

GAME_MATCH_WINDOW_HOURS = 24


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        logger.warning("invalid_datetime", value=value)
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


async def _find_game_by_matchup(
    db: AsyncSession,
    *,
    sport: str,
    home_team: str,
    away_team: str,
    start_time: datetime | None,
) -> Game | None:
    stmt = select(Game).where(
        Game.sport == sport,
        Game.home_team == home_team,
        Game.away_team == away_team,
    )
    result = await db.execute(stmt)
    candidates = result.scalars().all()
    if not candidates:
        return None
    if start_time is None:
        return candidates[0]

    for game in candidates:
        delta_hours = abs((game.start_time - start_time).total_seconds()) / 3600
        if delta_hours <= GAME_MATCH_WINDOW_HOURS:
            return game
    return None


async def upsert_game_from_scoreboard(db: AsyncSession, payload: dict) -> Game:
    espn_id = payload.get("espn_id")
    start_time = _parse_iso_datetime(payload.get("start_time")) or datetime.now(UTC)

    game: Game | None = None
    if espn_id:
        result = await db.execute(select(Game).where(Game.espn_id == espn_id))
        game = result.scalar_one_or_none()

    if game is None:
        game = await _find_game_by_matchup(
            db,
            sport=payload.get("sport", ""),
            home_team=payload.get("home_team", ""),
            away_team=payload.get("away_team", ""),
            start_time=start_time,
        )

    if game is None:
        game = Game(
            sport=payload.get("sport", ""),
            home_team=payload.get("home_team", ""),
            away_team=payload.get("away_team", ""),
            start_time=start_time,
            espn_id=espn_id,
            status=payload.get("status", "scheduled"),
        )
        db.add(game)
    else:
        game.sport = payload.get("sport", game.sport)
        game.home_team = payload.get("home_team", game.home_team)
        game.away_team = payload.get("away_team", game.away_team)
        game.start_time = start_time
        game.status = payload.get("status", game.status)
        if espn_id:
            game.espn_id = espn_id

    await db.flush()
    return game


async def record_opening_line(db: AsyncSession, payload: dict) -> Game:
    start_time = _parse_iso_datetime(payload.get("start_time")) or datetime.now(UTC)
    game = await _find_game_by_matchup(
        db,
        sport=payload.get("sport", ""),
        home_team=payload.get("home_team", ""),
        away_team=payload.get("away_team", ""),
        start_time=start_time,
    )

    if game is None:
        game = Game(
            sport=payload.get("sport", ""),
            home_team=payload.get("home_team", ""),
            away_team=payload.get("away_team", ""),
            start_time=start_time,
            status="scheduled",
            opening_line_home_prob=payload.get("home_prob"),
            opening_line_source=payload.get("source"),
        )
        db.add(game)
        await db.flush()
    else:
        game.opening_line_home_prob = payload.get("home_prob")
        game.opening_line_source = payload.get("source")

    opening_line = OpeningLine(
        game_id=game.id,
        source=payload.get("source", "unknown"),
        home_prob=payload.get("home_prob", 0.5),
        away_prob=payload.get("away_prob", 0.5),
        captured_at=_parse_iso_datetime(payload.get("captured_at")) or datetime.now(UTC),
        odds_raw=(
            json.dumps(payload.get("odds_raw")) if payload.get("odds_raw") is not None else None
        ),
    )
    db.add(opening_line)
    await db.flush()
    return game


async def record_game_event(db: AsyncSession, payload: dict) -> GameEvent | None:
    espn_id = payload.get("espn_id")
    if not espn_id:
        logger.warning("event_without_espn_id")
        return None

    result = await db.execute(select(Game).where(Game.espn_id == espn_id))
    game = result.scalar_one_or_none()
    if game is None:
        logger.warning("event_game_missing", espn_id=espn_id, event_type=payload.get("event_type"))
        return None

    game.status = payload.get("status", game.status)

    event = GameEvent(
        game_id=game.id,
        event_type=payload.get("event_type", "unknown"),
        description=payload.get("description"),
        home_score=payload.get("home_score"),
        away_score=payload.get("away_score"),
        period=payload.get("period"),
        clock=payload.get("clock"),
        detected_at=_parse_iso_datetime(payload.get("detected_at")) or datetime.now(UTC),
        estimated_real_at=_parse_iso_datetime(payload.get("estimated_real_at")),
        espn_data=(
            json.dumps(payload.get("espn_data")) if payload.get("espn_data") is not None else None
        ),
        classification=payload.get("classification"),
        confidence_score=payload.get("confidence_score"),
        kalshi_price_at=payload.get("kalshi_price_at"),
        baseline_prob=payload.get("baseline_prob"),
        deviation=payload.get("deviation"),
    )
    db.add(event)
    await db.flush()
    return event
