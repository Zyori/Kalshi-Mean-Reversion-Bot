import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from src.core.logging import get_logger
from src.core.types import Sport

logger = get_logger(__name__)

SCOREBOARD_URLS: dict[str, str] = {
    Sport.NHL: "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    Sport.NBA: "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    Sport.MLB: "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    Sport.NFL: "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    Sport.SOCCER: "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
    Sport.UFC: "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard",
}

POLL_INTERVAL_S = 10.0


def _parse_game(event: dict, sport: str) -> dict[str, Any]:
    competition = event["competitions"][0]
    teams = {t["homeAway"]: t["team"] for t in competition["competitors"]}
    scores = {t["homeAway"]: int(t.get("score", 0)) for t in competition["competitors"]}

    status = competition.get("status", {})
    status_type = status.get("type", {}).get("name", "unknown")
    period = str(status.get("period", ""))
    clock = status.get("displayClock", "")

    return {
        "espn_id": event["id"],
        "sport": sport,
        "home_team": teams.get("home", {}).get("displayName", ""),
        "away_team": teams.get("away", {}).get("displayName", ""),
        "home_score": scores.get("home", 0),
        "away_score": scores.get("away", 0),
        "status": status_type,
        "period": period,
        "clock": clock,
        "start_time": event.get("date"),
    }


class EspnScoreboardPoller:
    def __init__(self, queue: asyncio.Queue, sports: list[str] | None = None) -> None:
        self.queue = queue
        self.sports = sports or list(SCOREBOARD_URLS.keys())
        self.client = httpx.AsyncClient(timeout=10.0)
        self._previous: dict[str, dict] = {}
        self._last_poll: datetime | None = None
        self._status = "disconnected"

    @property
    def status(self) -> str:
        return self._status

    async def close(self) -> None:
        await self.client.aclose()

    async def poll_once(self) -> list[dict]:
        updates = []
        for sport in self.sports:
            url = SCOREBOARD_URLS.get(sport)
            if not url:
                continue
            try:
                resp = await self.client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, Exception):
                logger.exception("espn_scoreboard_error", sport=sport)
                continue

            for event in data.get("events", []):
                parsed = _parse_game(event, sport)
                espn_id = parsed["espn_id"]
                prev = self._previous.get(espn_id)

                if prev and (
                    prev["home_score"] != parsed["home_score"]
                    or prev["away_score"] != parsed["away_score"]
                    or prev["status"] != parsed["status"]
                ):
                    parsed["_change"] = "score_update"
                    updates.append(parsed)
                elif not prev:
                    parsed["_change"] = "new_game"
                    updates.append(parsed)

                self._previous[espn_id] = parsed

        self._last_poll = datetime.now(UTC)
        self._status = "connected"
        return updates

    async def _enqueue(self, data: dict) -> None:
        if self.queue.full():
            logger.warning("espn_scoreboard_queue_overflow")
        await self.queue.put(data)


async def espn_scoreboard_poller(queue: asyncio.Queue, sports: list[str] | None = None) -> None:
    poller = EspnScoreboardPoller(queue, sports)
    while True:
        try:
            updates = await poller.poll_once()
            for update in updates:
                await poller._enqueue(update)
            if updates:
                logger.info("espn_scoreboard_updates", count=len(updates))
        except Exception:
            logger.exception("espn_scoreboard_poll_error")
            poller._status = "error"
        await asyncio.sleep(POLL_INTERVAL_S)
