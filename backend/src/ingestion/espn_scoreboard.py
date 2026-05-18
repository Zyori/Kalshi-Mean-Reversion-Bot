import asyncio
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from src.config import settings
from src.core.logging import get_logger
from src.core.types import Sport

logger = get_logger(__name__)

_ESPN = "https://site.api.espn.com/apis/site/v2/sports"

# Per-sport ESPN scoreboard endpoints. A sport may map to multiple league
# scoreboards — for soccer we fan out across every major pro league plus
# the relevant international competitions, since Kalshi has historically
# listed markets from many of these and our paper-trade funnel benefits
# from every validated match we can ingest. ESPN dedupes by event_id, so
# the same game appearing in multiple feeds wouldn't be double-counted.
SCOREBOARD_URLS: dict[str, tuple[str, ...]] = {
    Sport.NHL: (f"{_ESPN}/hockey/nhl/scoreboard",),
    Sport.NBA: (f"{_ESPN}/basketball/nba/scoreboard",),
    Sport.MLB: (f"{_ESPN}/baseball/mlb/scoreboard",),
    Sport.NFL: (f"{_ESPN}/football/nfl/scoreboard",),
    Sport.UFC: (f"{_ESPN}/mma/ufc/scoreboard",),
    Sport.SOCCER: tuple(
        f"{_ESPN}/soccer/{league}/scoreboard"
        for league in (
            # Top 5 European leagues
            "eng.1",  # Premier League
            "esp.1",  # La Liga
            "ita.1",  # Serie A
            "ger.1",  # Bundesliga
            "fra.1",  # Ligue 1
            # Other major European leagues
            "por.1",  # Primeira Liga
            "ned.1",  # Eredivisie
            "bel.1",  # Belgian Pro League
            "sco.1",  # Scottish Premiership
            "tur.1",  # Süper Lig
            "cze.1",  # Czech First League (Chance Liga)
            # Americas
            "usa.1",  # MLS
            "mex.1",  # Liga MX
            "bra.1",  # Brasileirão Série A
            "arg.1",  # Liga Profesional
            # Asia / Oceania
            "jpn.1",  # J1 League
            "aus.1",  # A-League
            "chn.1",  # Chinese Super League
            "ksa.1",  # Saudi Pro League
            # UEFA & CONMEBOL club competitions
            "uefa.champions",
            "uefa.europa",
            "uefa.europa.conf",
            "conmebol.libertadores",
            "conmebol.sudamericana",
            # International (FIFA)
            "fifa.worldq.uefa",
            "fifa.worldq.conmebol",
            "fifa.worldq.concacaf",
            "fifa.worldq.afc",
            "fifa.worldq.caf",
            "fifa.worldq.ofc",
            "fifa.friendly",
            "fifa.world",  # World Cup itself when in season
        )
    ),
}

LIVE_STATUS_MARKERS = (
    "in_progress",
    "first_half",
    "second_half",
    "halftime",
    "end_period",
    "end_quarter",
    "overtime",
    "shootout",
    "intermission",
)
FINAL_STATUS_MARKERS = (
    "final",  # most US sports: STATUS_FINAL
    "post",  # legacy / alt
    "full_time",  # soccer: STATUS_FULL_TIME
    "ft",  # soccer abbreviation seen in some feeds
    "aet",  # soccer after-extra-time
    "canceled",  # rare but a terminal state
    "postponed",  # terminal for this date; will reschedule under a new id
    "abandoned",  # match called off mid-way
)
ESPN_PLATFORM_TIME_ZONE = ZoneInfo("America/New_York")


def is_live_status(status: str) -> bool:
    normalized = status.lower()
    return any(marker in normalized for marker in LIVE_STATUS_MARKERS)


def is_final_status(status: str) -> bool:
    normalized = status.lower()
    return any(marker in normalized for marker in FINAL_STATUS_MARKERS)


def _espn_dates_value(now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    eastern_date = current.astimezone(ESPN_PLATFORM_TIME_ZONE)
    return eastern_date.strftime("%Y%m%d")


def _parse_game(event: dict, sport: str) -> dict[str, Any]:
    competition = event["competitions"][0]
    competitors = competition["competitors"]
    teams = {}
    scores = {}
    for i, t in enumerate(competitors):
        side = t.get("homeAway", "home" if i == 0 else "away")
        teams[side] = t.get("team", {})
        scores[side] = int(t.get("score", 0))

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
        self._last_state = "idle"

    @property
    def status(self) -> str:
        return self._status

    async def close(self) -> None:
        await self.client.aclose()

    async def _fetch_url_events(
        self, url: str, sport: str, dates_value: str
    ) -> dict[str, dict[str, Any]]:
        """Hit one ESPN scoreboard URL twice (default + dates=today) and
        return its events keyed by ESPN event id. Errors are logged and
        return an empty dict so one bad league never blocks the rest."""
        try:
            default_resp, today_resp = await asyncio.gather(
                self.client.get(url),
                self.client.get(url, params={"dates": dates_value}),
            )
        except (httpx.HTTPError, Exception):
            logger.exception("espn_scoreboard_error", sport=sport, url=url)
            return {}

        events_by_id: dict[str, dict[str, Any]] = {}
        for resp, label in ((default_resp, "default"), (today_resp, "today")):
            try:
                resp.raise_for_status()
            except httpx.HTTPError:
                logger.warning(
                    "espn_scoreboard_response_error",
                    sport=sport,
                    url=url,
                    request_type=label,
                    status_code=resp.status_code,
                )
                continue
            for event in resp.json().get("events", []):
                event_id = event.get("id")
                if event_id:
                    events_by_id[event_id] = event
        return events_by_id

    async def poll_once(self) -> list[dict]:
        updates = []
        has_live_game = False
        has_upcoming_game = False
        dates_value = _espn_dates_value()
        for sport in self.sports:
            urls = SCOREBOARD_URLS.get(sport)
            if not urls:
                continue
            # ESPN dedupes by event_id across feeds, so the same game listed
            # by two competition endpoints (e.g. a UCL match also on eng.1)
            # is only processed once.
            events_by_id: dict[str, dict[str, Any]] = {}
            for url in urls:
                events_by_id.update(await self._fetch_url_events(url, sport, dates_value))

            for event in events_by_id.values():
                parsed = _parse_game(event, sport)
                espn_id = parsed["espn_id"]
                prev = self._previous.get(espn_id)
                status = parsed["status"].lower()

                if is_live_status(status):
                    has_live_game = True
                elif not is_final_status(status):
                    has_upcoming_game = True

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
        if has_live_game:
            self._last_state = "live"
        elif has_upcoming_game:
            self._last_state = "pregame"
        else:
            self._last_state = "idle"
        return updates

    def next_interval(self) -> float:
        if self._last_state == "live":
            return settings.scoreboard_live_poll_interval_s
        if self._last_state == "pregame":
            return settings.scoreboard_pregame_poll_interval_s
        return settings.scoreboard_idle_poll_interval_s

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
        await asyncio.sleep(poller.next_interval())
