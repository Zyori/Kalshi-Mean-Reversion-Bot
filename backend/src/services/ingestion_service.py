import json
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.game import Game, GameEvent
from src.models.market import Market, OpeningLine

logger = get_logger(__name__)

GAME_MATCH_WINDOW_HOURS = 3


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


def _coerce_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _is_live_game(status: str | None) -> bool:
    normalized = str(status or "").lower()
    return any(
        marker in normalized
        for marker in (
            "in_progress",
            "first_half",
            "second_half",
            "halftime",
            "end_period",
            "end_quarter",
            "overtime",
            "shootout",
            "intermission",
            "live",
        )
    )


def _is_final_game(status: str | None) -> bool:
    normalized = str(status or "").lower()
    return any(marker in normalized for marker in ("final", "post", "full_time"))


def _game_quality_score(game: Game) -> tuple[int, int, int, int, int]:
    structured_score = sum(
        value is not None
        for value in (
            game.opening_line_home_prob,
            game.opening_spread_home,
            game.opening_total,
            game.latest_home_score,
            game.latest_away_score,
            game.final_home_score,
            game.final_away_score,
        )
    )
    return (
        1 if _is_live_game(game.status) else 0,
        1 if _is_final_game(game.status) else 0,
        1 if bool(game.espn_id) else 0,
        structured_score,
        -(game.id or 0),
    )


def _game_time_delta_hours(game: Game, start_time: datetime | None) -> float:
    if start_time is None:
        return 0.0
    game_start = _coerce_utc(game.start_time)
    if game_start is None:
        return float("inf")
    return abs((game_start - start_time).total_seconds()) / 3600


def _merge_game_fields(target: Game, source: Game) -> None:
    if target.espn_id is None and source.espn_id is not None:
        target.espn_id = source.espn_id
    if (
        not _is_live_game(target.status)
        and not _is_final_game(target.status)
        and (_is_live_game(source.status) or _is_final_game(source.status))
    ):
        target.status = source.status
    if target.opening_line_home_prob is None:
        target.opening_line_home_prob = source.opening_line_home_prob
    if target.opening_line_source is None:
        target.opening_line_source = source.opening_line_source
    if target.opening_spread_home is None:
        target.opening_spread_home = source.opening_spread_home
    if target.opening_spread_away is None:
        target.opening_spread_away = source.opening_spread_away
    if target.opening_total is None:
        target.opening_total = source.opening_total
    if target.opening_home_team_total is None:
        target.opening_home_team_total = source.opening_home_team_total
    if target.opening_away_team_total is None:
        target.opening_away_team_total = source.opening_away_team_total
    if target.latest_home_score is None:
        target.latest_home_score = source.latest_home_score
    if target.latest_away_score is None:
        target.latest_away_score = source.latest_away_score
    if target.final_home_score is None:
        target.final_home_score = source.final_home_score
    if target.final_away_score is None:
        target.final_away_score = source.final_away_score


async def _find_game_duplicates(
    db: AsyncSession,
    *,
    game: Game,
) -> list[Game]:
    game_start = _coerce_utc(game.start_time)
    stmt = select(Game).where(
        Game.id != game.id,
        Game.sport == game.sport,
        Game.home_team == game.home_team,
        Game.away_team == game.away_team,
    )
    result = await db.execute(stmt)
    candidates = result.scalars().all()
    duplicates: list[Game] = []
    for candidate in candidates:
        if _game_time_delta_hours(candidate, game_start) <= GAME_MATCH_WINDOW_HOURS:
            duplicates.append(candidate)
    return duplicates


async def _merge_duplicate_games(
    db: AsyncSession,
    *,
    canonical: Game,
    duplicates: list[Game],
) -> None:
    for duplicate in duplicates:
        if duplicate.id == canonical.id:
            continue
        _merge_game_fields(canonical, duplicate)
        await db.execute(
            update(OpeningLine)
            .where(OpeningLine.game_id == duplicate.id)
            .values(game_id=canonical.id)
        )
        await db.execute(
            update(GameEvent)
            .where(GameEvent.game_id == duplicate.id)
            .values(game_id=canonical.id)
        )
        await db.execute(
            update(Market)
            .where(Market.game_id == duplicate.id)
            .values(game_id=canonical.id)
        )
        await db.delete(duplicate)


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

    best_match: tuple[tuple[int, int, int, int, int], float, Game] | None = None
    for game in candidates:
        delta_hours = _game_time_delta_hours(game, start_time)
        if delta_hours > GAME_MATCH_WINDOW_HOURS:
            continue
        candidate_key = (_game_quality_score(game), -delta_hours)
        if best_match is None or candidate_key > (best_match[0], -best_match[1]):
            best_match = (_game_quality_score(game), delta_hours, game)
    return best_match[2] if best_match else None


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
            latest_home_score=payload.get("home_score"),
            latest_away_score=payload.get("away_score"),
        )
        db.add(game)
    else:
        game.sport = payload.get("sport", game.sport)
        game.home_team = payload.get("home_team", game.home_team)
        game.away_team = payload.get("away_team", game.away_team)
        game.start_time = start_time
        game.status = payload.get("status", game.status)
        game.latest_home_score = payload.get("home_score")
        game.latest_away_score = payload.get("away_score")
        if espn_id:
            game.espn_id = espn_id
    normalized_status = str(payload.get("status", "")).lower()
    if normalized_status in {"final", "status_final", "post"}:
        game.final_home_score = payload.get("home_score")
        game.final_away_score = payload.get("away_score")
    else:
        game.final_home_score = None
        game.final_away_score = None

    duplicates = await _find_game_duplicates(db, game=game)
    if duplicates:
        await _merge_duplicate_games(db, canonical=game, duplicates=duplicates)

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
            opening_spread_home=payload.get("home_spread"),
            opening_spread_away=payload.get("away_spread"),
            opening_total=payload.get("total_points"),
            opening_home_team_total=payload.get("home_team_total"),
            opening_away_team_total=payload.get("away_team_total"),
        )
        db.add(game)
        await db.flush()
    else:
        game.opening_line_home_prob = payload.get("home_prob")
        game.opening_line_source = payload.get("source")
        game.opening_spread_home = payload.get("home_spread")
        game.opening_spread_away = payload.get("away_spread")
        game.opening_total = payload.get("total_points")
        game.opening_home_team_total = payload.get("home_team_total")
        game.opening_away_team_total = payload.get("away_team_total")

    duplicates = await _find_game_duplicates(db, game=game)
    if duplicates:
        await _merge_duplicate_games(db, canonical=game, duplicates=duplicates)

    opening_line = OpeningLine(
        game_id=game.id,
        source=payload.get("source", "unknown"),
        home_prob=payload.get("home_prob", 0.5),
        away_prob=payload.get("away_prob", 0.5),
        home_spread=payload.get("home_spread"),
        away_spread=payload.get("away_spread"),
        total_points=payload.get("total_points"),
        home_team_total=payload.get("home_team_total"),
        away_team_total=payload.get("away_team_total"),
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

    espn_data = payload.get("espn_data")
    if isinstance(espn_data, dict):
        stored_espn_data = {
            **espn_data,
            "market_category": payload.get("market_category"),
            "market_source": payload.get("market_source"),
            "market_label_yes": payload.get("market_label_yes"),
            "market_label_no": payload.get("market_label_no"),
        }
    else:
        stored_espn_data = {
            "market_category": payload.get("market_category"),
            "market_source": payload.get("market_source"),
            "market_label_yes": payload.get("market_label_yes"),
            "market_label_no": payload.get("market_label_no"),
        }

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
        espn_data=json.dumps(stored_espn_data),
        classification=payload.get("classification"),
        confidence_score=payload.get("confidence_score"),
        kalshi_price_at=payload.get("kalshi_price_at"),
        baseline_prob=payload.get("baseline_prob"),
        deviation=payload.get("deviation"),
    )
    db.add(event)
    await db.flush()
    return event
