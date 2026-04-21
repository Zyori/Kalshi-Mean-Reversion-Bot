from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_db
from src.api.serializers import serialize_event, serialize_game
from src.models.game import Game, GameEvent

router = APIRouter(prefix="/api")


@router.get("/games")
async def list_games(
    sport: str | None = None,
    status: str | None = None,
    days_ahead: int | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Game)
    if sport:
        stmt = stmt.where(Game.sport == sport)
    if status:
        stmt = stmt.where(Game.status == status)
    if days_ahead is not None:
        now = datetime.now(UTC)
        window_end = now + timedelta(days=days_ahead)
        window_start = now - timedelta(hours=12)
        live_like = Game.status.in_(["STATUS_IN_PROGRESS", "STATUS_END_PERIOD", "live"])
        stmt = stmt.where(
            or_(
                live_like,
                and_(Game.start_time >= window_start, Game.start_time <= window_end),
            )
        )
    stmt = stmt.order_by(Game.start_time.asc()).limit(limit)
    result = await db.execute(stmt)
    return [serialize_game(game) for game in result.scalars().all()]


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
