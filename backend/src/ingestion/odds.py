import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from src.config import settings
from src.core.logging import get_logger
from src.core.types import Sport

logger = get_logger(__name__)

ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"

SPORT_KEYS: dict[str, str] = {
    Sport.NHL: "icehockey_nhl",
    Sport.NBA: "basketball_nba",
    Sport.MLB: "baseball_mlb",
    Sport.NFL: "americanfootball_nfl",
    Sport.SOCCER: "soccer_epl",
    Sport.UFC: "mma_mixed_martial_arts",
}

def american_to_implied_prob(odds: int) -> float:
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def _parse_odds_response(data: list[dict], sport: str) -> list[dict[str, Any]]:
    results = []
    for game in data:
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")
        start_time = game.get("commence_time", "")

        for bookmaker in game.get("bookmakers", []):
            source = bookmaker.get("key", "")
            for market in bookmaker.get("markets", []):
                if market.get("key") != "h2h":
                    continue

                outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
                home_odds = outcomes.get(home_team)
                away_odds = outcomes.get(away_team)

                if home_odds is None or away_odds is None:
                    continue

                home_prob = american_to_implied_prob(home_odds)
                away_prob = american_to_implied_prob(away_odds)

                results.append(
                    {
                        "sport": sport,
                        "home_team": home_team,
                        "away_team": away_team,
                        "start_time": start_time,
                        "source": source,
                        "home_prob": round(home_prob, 4),
                        "away_prob": round(away_prob, 4),
                        "odds_raw": {"home": home_odds, "away": away_odds},
                        "captured_at": datetime.now(UTC).isoformat(),
                    }
                )
            break  # first bookmaker only for opening line capture

    return results


class OddsApiPoller:
    def __init__(self, queue: asyncio.Queue, sports: list[str] | None = None) -> None:
        self.queue = queue
        self.sports = sports or list(SPORT_KEYS.keys())
        self.api_key = settings.odds_api_key
        self.client = httpx.AsyncClient(timeout=15.0)
        self._status = "disconnected"
        self._requests_used = 0

    @property
    def status(self) -> str:
        return self._status

    async def close(self) -> None:
        await self.client.aclose()

    async def poll_once(self) -> list[dict]:
        if not self.api_key:
            logger.warning("odds_api_no_key")
            return []

        all_odds: list[dict] = []
        for sport in self.sports:
            sport_key = SPORT_KEYS.get(sport)
            if not sport_key:
                continue

            try:
                resp = await self.client.get(
                    f"{ODDS_API_BASE}/{sport_key}/odds",
                    params={
                        "apiKey": self.api_key,
                        "regions": "us",
                        "markets": "h2h",
                        "oddsFormat": "american",
                    },
                )
                remaining = resp.headers.get("x-requests-remaining", "?")
                self._requests_used += 1
                logger.info(
                    "odds_api_request",
                    sport=sport,
                    remaining=remaining,
                    used=self._requests_used,
                )

                resp.raise_for_status()
                data = resp.json()
                all_odds.extend(_parse_odds_response(data, sport))

            except (httpx.HTTPError, Exception):
                logger.exception("odds_api_error", sport=sport)
                continue

        self._status = "connected" if all_odds else self._status
        return all_odds

    async def _enqueue(self, data: dict) -> None:
        if self.queue.full():
            logger.warning("odds_api_queue_overflow")
        await self.queue.put(data)


async def odds_poller(queue: asyncio.Queue, sports: list[str] | None = None) -> None:
    poller = OddsApiPoller(queue, sports)
    while True:
        try:
            odds = await poller.poll_once()
            for line in odds:
                await poller._enqueue(line)
            if odds:
                logger.info("odds_api_captured", count=len(odds))
        except Exception:
            logger.exception("odds_api_poll_error")
            poller._status = "error"
        await asyncio.sleep(settings.odds_poll_interval_s)
