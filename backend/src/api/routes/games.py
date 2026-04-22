from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_db
from src.api.serializers import serialize_event, serialize_game
from src.models.game import Game, GameEvent

router = APIRouter(prefix="/api")
DISPLAY_GAME_MATCH_WINDOW_HOURS = 3


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _status_rank(status: str) -> tuple[int, int]:
    normalized = status.lower()
    is_live = int("in_progress" in normalized or "end_period" in normalized or normalized == "live")
    is_final = int("final" in normalized or "post" in normalized or "full_time" in normalized)
    return (is_live, is_final)


def _game_quality(game: Game) -> tuple[int, int, int, int]:
    data_score = sum(
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
    live_rank, final_rank = _status_rank(game.status)
    return (live_rank, final_rank, int(bool(game.espn_id)), data_score)


def _should_group_games(left: Game, right: Game) -> bool:
    if left.sport != right.sport:
        return False
    if left.home_team != right.home_team or left.away_team != right.away_team:
        return False
    left_start = _coerce_utc(left.start_time)
    right_start = _coerce_utc(right.start_time)
    delta_hours = abs((left_start - right_start).total_seconds()) / 3600
    return delta_hours <= DISPLAY_GAME_MATCH_WINDOW_HOURS


def _pick_display_game(games: list[Game]) -> Game:
    canonical = max(games, key=_game_quality)
    for duplicate in games:
        if duplicate.id == canonical.id:
            continue
        if canonical.espn_id is None and duplicate.espn_id is not None:
            canonical.espn_id = duplicate.espn_id
        if canonical.opening_line_home_prob is None:
            canonical.opening_line_home_prob = duplicate.opening_line_home_prob
        if canonical.opening_line_source is None:
            canonical.opening_line_source = duplicate.opening_line_source
        if canonical.opening_spread_home is None:
            canonical.opening_spread_home = duplicate.opening_spread_home
        if canonical.opening_spread_away is None:
            canonical.opening_spread_away = duplicate.opening_spread_away
        if canonical.opening_total is None:
            canonical.opening_total = duplicate.opening_total
        if canonical.opening_home_team_total is None:
            canonical.opening_home_team_total = duplicate.opening_home_team_total
        if canonical.opening_away_team_total is None:
            canonical.opening_away_team_total = duplicate.opening_away_team_total
    return canonical


def _dedupe_games(games: list[Game]) -> list[Game]:
    groups: list[list[Game]] = []
    for game in games:
        for group in groups:
            if _should_group_games(group[0], game):
                group.append(game)
                break
        else:
            groups.append([game])
    return [_pick_display_game(group) for group in groups]


@router.get("/games")
async def list_games(
    sport: str | None = None,
    status: str | None = None,
    days_ahead: int | None = None,
    days_back: int | None = None,
    limit: int = 50,
    sort: str = "asc",
    db: AsyncSession = Depends(get_db),
):
    fetch_limit = max(limit * 4, limit)
    stmt = select(Game)
    if sport:
        stmt = stmt.where(Game.sport == sport)
    if status:
        stmt = stmt.where(Game.status == status)
    if days_ahead is not None or days_back is not None:
        now = datetime.now(UTC)
        window_end = now + timedelta(days=days_ahead or 0)
        window_start = now - timedelta(days=days_back or 0)
        if days_ahead is not None and days_back is None:
            window_start = now - timedelta(hours=12)
        live_like = Game.status.in_(["STATUS_IN_PROGRESS", "STATUS_END_PERIOD", "live"])
        stmt = stmt.where(
            or_(
                live_like,
                and_(Game.start_time >= window_start, Game.start_time <= window_end),
            )
        )
    if sort == "desc":
        stmt = stmt.order_by(Game.start_time.desc())
    else:
        stmt = stmt.order_by(Game.start_time.asc())
    stmt = stmt.limit(fetch_limit)
    result = await db.execute(stmt)
    games = _dedupe_games(result.scalars().all())
    if sort == "desc":
        games.sort(key=lambda game: _coerce_utc(game.start_time), reverse=True)
    else:
        games.sort(key=lambda game: _coerce_utc(game.start_time))
    return [serialize_game(game) for game in games[:limit]]


@router.get("/games/{game_id}")
async def get_game(game_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Game)
        .where(Game.id == game_id)
        .options(selectinload(Game.events), selectinload(Game.opening_lines))
    )
    result = await db.execute(stmt)
    game = result.scalar_one_or_none()
    if not game:
        return {"error": "Game not found"}, 404
    payload = serialize_game(game)
    payload["events"] = [
        serialize_event(event)
        for event in sorted(
            game.events,
            key=lambda e: e.detected_at.isoformat() if e.detected_at else "",
            reverse=True,
        )
    ]
    payload["opening_lines"] = [
        {
            "id": line.id,
            "source": line.source,
            "home_prob": line.home_prob,
            "away_prob": line.away_prob,
            "home_spread": line.home_spread,
            "away_spread": line.away_spread,
            "total_points": line.total_points,
            "home_team_total": line.home_team_total,
            "away_team_total": line.away_team_total,
            "captured_at": line.captured_at.isoformat() if line.captured_at else None,
        }
        for line in sorted(
            game.opening_lines,
            key=lambda opening_line: (
                opening_line.captured_at.isoformat() if opening_line.captured_at else ""
            ),
            reverse=True,
        )
    ]
    return payload


@router.get("/games/{game_id}/events")
async def get_game_events(game_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(GameEvent)
        .options(selectinload(GameEvent.game))
        .where(GameEvent.game_id == game_id)
        .order_by(GameEvent.detected_at.desc())
    )
    result = await db.execute(stmt)
    return [serialize_event(event) for event in result.scalars().all()]
