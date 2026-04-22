import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from src.config import settings
from src.core.logging import get_logger
from src.core.types import Sport

logger = get_logger(__name__)

ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"
PRIMARY_MARKETS = "h2h,spreads,totals,team_totals"
FALLBACK_MARKETS = "h2h,spreads,totals"

SPORT_KEYS: dict[str, str] = {
    Sport.NHL: "icehockey_nhl",
    Sport.NBA: "basketball_nba",
    Sport.MLB: "baseball_mlb",
    Sport.NFL: "americanfootball_nfl",
    Sport.SOCCER: "soccer_epl",
    Sport.UFC: "mma_mixed_martial_arts",
}


def _find_market(markets: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    for market in markets:
        if market.get("key") == key:
            return market
    return None


def _parse_h2h_market(
    market: dict[str, Any] | None,
    home_team: str,
    away_team: str,
) -> tuple[float | None, float | None, dict[str, Any]]:
    if market is None:
        return None, None, {}

    outcomes = {outcome["name"]: outcome["price"] for outcome in market.get("outcomes", [])}
    home_odds = outcomes.get(home_team)
    away_odds = outcomes.get(away_team)
    if home_odds is None or away_odds is None:
        return None, None, {}

    return (
        round(american_to_implied_prob(home_odds), 4),
        round(american_to_implied_prob(away_odds), 4),
        {"home": home_odds, "away": away_odds},
    )


def _parse_spread_market(
    market: dict[str, Any] | None,
    home_team: str,
    away_team: str,
) -> tuple[float | None, float | None, dict[str, Any]]:
    if market is None:
        return None, None, {}

    by_name = {outcome.get("name"): outcome for outcome in market.get("outcomes", [])}
    home = by_name.get(home_team)
    away = by_name.get(away_team)
    if home is None or away is None:
        return None, None, {}

    home_point = home.get("point")
    away_point = away.get("point")
    if home_point is None or away_point is None:
        return None, None, {}

    return (
        float(home_point),
        float(away_point),
        {
            "home": {"point": home_point, "price": home.get("price")},
            "away": {"point": away_point, "price": away.get("price")},
        },
    )


def _parse_total_market(market: dict[str, Any] | None) -> tuple[float | None, dict[str, Any]]:
    if market is None:
        return None, {}

    outcomes = market.get("outcomes", [])
    over = next(
        (
            outcome
            for outcome in outcomes
            if str(outcome.get("name", "")).lower() == "over"
        ),
        None,
    )
    under = next(
        (
            outcome
            for outcome in outcomes
            if str(outcome.get("name", "")).lower() == "under"
        ),
        None,
    )
    if over is not None:
        point = over.get("point")
    elif under is not None:
        point = under.get("point")
    else:
        point = None
    if point is None:
        return None, {}

    return (
        float(point),
        {
            "over": {"point": over.get("point"), "price": over.get("price")} if over else None,
            "under": {"point": under.get("point"), "price": under.get("price")} if under else None,
        },
    )


def _team_total_outcome_team(outcome: dict[str, Any]) -> str:
    fields = [
        outcome.get("description"),
        outcome.get("participant"),
        outcome.get("team"),
        outcome.get("name"),
    ]
    for field in fields:
        if field:
            return str(field)
    return ""


def _parse_team_totals_market(
    market: dict[str, Any] | None,
    home_team: str,
    away_team: str,
) -> tuple[float | None, float | None, dict[str, Any]]:
    if market is None:
        return None, None, {}

    home_total: float | None = None
    away_total: float | None = None
    home_raw: list[dict[str, Any]] = []
    away_raw: list[dict[str, Any]] = []

    for outcome in market.get("outcomes", []):
        point = outcome.get("point")
        if point is None:
            continue
        label = _team_total_outcome_team(outcome).lower()
        raw_outcome = {
            "name": outcome.get("name"),
            "description": outcome.get("description"),
            "point": point,
            "price": outcome.get("price"),
        }
        if home_team.lower() in label:
            home_total = float(point)
            home_raw.append(raw_outcome)
        elif away_team.lower() in label:
            away_total = float(point)
            away_raw.append(raw_outcome)

    if home_total is None and away_total is None:
        return None, None, {}

    return home_total, away_total, {"home": home_raw, "away": away_raw}

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
            markets = bookmaker.get("markets", [])
            home_prob, away_prob, odds_raw = _parse_h2h_market(
                _find_market(markets, "h2h"),
                home_team,
                away_team,
            )
            home_spread, away_spread, spread_raw = _parse_spread_market(
                _find_market(markets, "spreads"),
                home_team,
                away_team,
            )
            total_points, totals_raw = _parse_total_market(_find_market(markets, "totals"))
            home_team_total, away_team_total, team_totals_raw = _parse_team_totals_market(
                _find_market(markets, "team_totals"),
                home_team,
                away_team,
            )

            if home_prob is None or away_prob is None:
                continue

            results.append(
                {
                    "sport": sport,
                    "home_team": home_team,
                    "away_team": away_team,
                    "start_time": start_time,
                    "source": source,
                    "home_prob": home_prob,
                    "away_prob": away_prob,
                    "home_spread": home_spread,
                    "away_spread": away_spread,
                    "total_points": total_points,
                    "home_team_total": home_team_total,
                    "away_team_total": away_team_total,
                    "odds_raw": {
                        "h2h": odds_raw,
                        "spreads": spread_raw,
                        "totals": totals_raw,
                        "team_totals": team_totals_raw,
                    },
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
        self._markets_by_sport_key: dict[str, str] = {}

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
                resp = await self._fetch_odds(sport_key)
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

    async def _fetch_odds(self, sport_key: str) -> httpx.Response:
        requested_markets = self._markets_by_sport_key.get(sport_key, PRIMARY_MARKETS)
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": requested_markets,
            "oddsFormat": "american",
        }
        resp = await self.client.get(f"{ODDS_API_BASE}/{sport_key}/odds", params=params)
        if resp.status_code not in {400, 422} or requested_markets == FALLBACK_MARKETS:
            return resp

        logger.warning(
            "odds_api_market_fallback",
            sport_key=sport_key,
            requested=requested_markets,
            fallback=FALLBACK_MARKETS,
            status=resp.status_code,
        )
        self._markets_by_sport_key[sport_key] = FALLBACK_MARKETS
        fallback_params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": FALLBACK_MARKETS,
            "oddsFormat": "american",
        }
        return await self.client.get(f"{ODDS_API_BASE}/{sport_key}/odds", params=fallback_params)

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
