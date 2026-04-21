from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_db
from src.api.serializers import serialize_event
from src.models.game import GameEvent

router = APIRouter(prefix="/api")


@router.get("/events")
async def list_events(
    sport: str | None = None,
    event_type: str | None = None,
    classification: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(GameEvent)
        .options(selectinload(GameEvent.game))
        .order_by(GameEvent.detected_at.desc())
        .limit(limit)
    )
    if sport:
        stmt = stmt.join(GameEvent.game).where(GameEvent.game.has(sport=sport))
    if event_type:
        stmt = stmt.where(GameEvent.event_type == event_type)
    if classification:
        stmt = stmt.where(GameEvent.classification == classification)
    result = await db.execute(stmt)
    return [serialize_event(event) for event in result.scalars().all()]
