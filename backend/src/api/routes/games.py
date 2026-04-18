from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_db
from src.models.game import Game, GameEvent

router = APIRouter(prefix="/api")


@router.get("/games")
async def list_games(
    sport: str | None = None,
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Game).order_by(Game.start_time.desc()).limit(limit)
    if sport:
        stmt = stmt.where(Game.sport == sport)
    if status:
        stmt = stmt.where(Game.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()


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
    return game


@router.get("/games/{game_id}/events")
async def get_game_events(game_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(GameEvent).where(GameEvent.game_id == game_id).order_by(GameEvent.detected_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
