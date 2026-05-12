"""Per-sport configuration API.

Exposes the SportConfigRegistry so the dashboard knows which sports to render
as active vs passive vs hidden. The DB is the source of truth; the runtime
registry is just a cache, and this route reflects whatever the registry holds.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from src.core.types import Sport, SportMode
from src.supervisor import registry

router = APIRouter()


class SportEntry(BaseModel):
    sport: Sport
    mode: SportMode
    notes: str | None = None


class SportsResponse(BaseModel):
    sports: list[SportEntry]


@router.get("/api/sports", response_model=SportsResponse)
async def list_sports() -> SportsResponse:
    cfg = registry.sport_config
    entries = [
        SportEntry(sport=sport, mode=cfg.mode(sport)) for sport in Sport
    ]
    return SportsResponse(sports=entries)
