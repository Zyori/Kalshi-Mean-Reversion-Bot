"""In-memory registry of per-sport engagement modes.

The DB (`sport_configs` table) is the durable source of truth; this module is
the runtime cache that every other component reads. Loaded once at supervisor
startup, refreshed on demand via `reload()` if/when the API exposes a mutation
endpoint. There is no parallel hardcoded list of "active sports" anywhere
else in the codebase — adding/promoting a sport is a DB row change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.core.logging import get_logger
from src.core.types import Sport, SportMode
from src.models import SportConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class SportConfigRegistry:
    def __init__(self, modes: dict[Sport, SportMode] | None = None) -> None:
        self._modes: dict[Sport, SportMode] = modes or {}

    @classmethod
    async def load(cls, db: AsyncSession) -> SportConfigRegistry:
        result = await db.execute(select(SportConfig))
        modes = {row.sport: row.mode for row in result.scalars()}
        # Defensive: any Sport missing from the table defaults to OFF rather
        # than silently behaving like ACTIVE.
        for sport in Sport:
            modes.setdefault(sport, SportMode.OFF)
        logger.info(
            "sport_config_loaded",
            modes={sport.value: mode.value for sport, mode in modes.items()},
        )
        return cls(modes)

    async def reload(self, db: AsyncSession) -> None:
        refreshed = await self.load(db)
        self._modes = refreshed._modes

    def mode(self, sport: Sport | str) -> SportMode:
        return self._modes.get(Sport(sport), SportMode.OFF)

    def is_active(self, sport: Sport | str) -> bool:
        return self.mode(sport) == SportMode.ACTIVE

    def is_passive(self, sport: Sport | str) -> bool:
        return self.mode(sport) == SportMode.PASSIVE

    def is_polled(self, sport: Sport | str) -> bool:
        """True for both active and passive — anything we collect schedules for."""
        return self.mode(sport) in (SportMode.ACTIVE, SportMode.PASSIVE)

    def active_sports(self) -> list[Sport]:
        return [s for s, m in self._modes.items() if m == SportMode.ACTIVE]

    def polled_sports(self) -> list[Sport]:
        return [s for s, m in self._modes.items() if m != SportMode.OFF]

    def as_dict(self) -> dict[str, str]:
        return {sport.value: mode.value for sport, mode in self._modes.items()}
