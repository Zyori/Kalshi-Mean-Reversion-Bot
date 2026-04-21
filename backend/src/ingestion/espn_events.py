import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from src.config import settings
from src.core.logging import get_logger
from src.core.types import Sport

logger = get_logger(__name__)

SUMMARY_BASE = "https://site.web.api.espn.com/apis/site/v2/sports"

SPORT_PATHS: dict[str, str] = {
    Sport.NHL: "hockey/nhl",
    Sport.NBA: "basketball/nba",
    Sport.MLB: "baseball/mlb",
    Sport.NFL: "football/nfl",
    Sport.SOCCER: "soccer/eng.1",
    Sport.UFC: "mma/ufc",
}

LATENCY_ESTIMATES: dict[str, timedelta] = {
    Sport.NHL: timedelta(seconds=15),
    Sport.NBA: timedelta(seconds=15),
    Sport.MLB: timedelta(seconds=10),
    Sport.NFL: timedelta(seconds=20),
    Sport.SOCCER: timedelta(seconds=20),
    Sport.UFC: timedelta(seconds=15),
}


COMMON_EVENT_MARKERS = (
    "injury",
    "timeout",
    "review",
    "challenged",
    "challenge",
    "ejection",
    "controvers",
    "delay",
    "weather",
    "official",
)

SPORT_EVENT_MARKERS: dict[str, tuple[str, ...]] = {
    Sport.NHL: (
        "goal",
        "penalty",
        "power play",
        "shorthanded",
        "empty net",
        "goalie pulled",
        "goalie change",
        "injured",
    ),
    Sport.NBA: (
        "technical",
        "flagrant",
        "ejection",
        "timeout",
        "foul trouble",
        "injury",
        "review",
        "challenge",
    ),
    Sport.MLB: (
        "home run",
        "pitching change",
        "mound visit",
        "injury",
        "ejection",
        "review",
        "error",
    ),
    Sport.NFL: (
        "touchdown",
        "turnover",
        "interception",
        "fumble",
        "penalty",
        "sack",
        "timeout",
        "injury",
        "challenge",
        "review",
        "two-point",
        "field goal",
    ),
    Sport.SOCCER: (
        "goal",
        "red card",
        "yellow card",
        "penalty",
        "substitution",
        "var",
        "injury",
        "stoppage",
        "own goal",
    ),
    Sport.UFC: (
        "knockdown",
        "takedown",
        "submission",
        "doctor",
        "injury",
        "point deduction",
        "timeout",
    ),
}

SCORING_RUN_PATTERN = re.compile(r"\b\d{1,2}-\d{1,2}\s+run\b")


def _event_context(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "header": data.get("header"),
        "boxscore": data.get("boxscore"),
        "leaders": data.get("leaders"),
        "injuries": data.get("injuries"),
        "predictor": data.get("predictor"),
        "winprobability": data.get("winprobability"),
        "broadcasts": data.get("broadcasts"),
    }


def _score_from_context(context: dict[str, Any]) -> tuple[int | None, int | None]:
    header = context.get("header") or {}
    competitions = header.get("competitions") or []
    if competitions:
        competitors = competitions[0].get("competitors") or []
        scores: dict[str, int | None] = {"home": None, "away": None}
        for index, competitor in enumerate(competitors):
            side = competitor.get("homeAway", "home" if index == 0 else "away")
            score_raw = competitor.get("score")
            try:
                scores[side] = int(score_raw) if score_raw is not None else None
            except (TypeError, ValueError):
                scores[side] = None
        return scores["home"], scores["away"]
    return None, None


def _score_from_play(
    play: dict[str, Any],
    context: dict[str, Any],
) -> tuple[int | None, int | None]:
    for home_key, away_key in (
        ("homeScore", "awayScore"),
        ("home_score", "away_score"),
    ):
        home_score = play.get(home_key)
        away_score = play.get(away_key)
        if home_score is not None and away_score is not None:
            try:
                return int(home_score), int(away_score)
            except (TypeError, ValueError):
                pass
    return _score_from_context(context)


def _extract_events(plays: list[dict], sport: str, context: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    for play in plays:
        raw_event_type = play.get("type", {}).get("text", "")
        description = play.get("text", "")
        event_type = _normalize_event_type(raw_event_type, description, sport)

        is_significant = _is_significant_event(raw_event_type, description, sport)
        if not is_significant:
            continue

        now = datetime.now(UTC)
        latency = LATENCY_ESTIMATES.get(sport, timedelta(seconds=15))
        home_score, away_score = _score_from_play(play, context)

        events.append(
            {
                "event_type": event_type,
                "description": description,
                "home_score": home_score,
                "away_score": away_score,
                "period": str(play.get("period", {}).get("number", "")),
                "clock": play.get("clock", {}).get("displayValue", ""),
                "detected_at": now.isoformat(),
                "estimated_real_at": (now - latency).isoformat(),
                "espn_data": {
                    "play": play,
                    "context": context,
                    "raw_event_type": raw_event_type,
                    "normalized_event_type": event_type,
                },
            }
        )
    return events


def _is_significant_event(event_type: str, description: str, sport: str) -> bool:
    et_lower = event_type.lower()
    desc_lower = description.lower()
    search_text = f"{et_lower} {desc_lower}"

    if any(marker in search_text for marker in COMMON_EVENT_MARKERS):
        return True
    if sport == Sport.NBA and SCORING_RUN_PATTERN.search(search_text):
        return True

    sport_markers = SPORT_EVENT_MARKERS.get(sport, ())
    return any(marker in search_text for marker in sport_markers)


def _normalize_event_type(event_type: str, description: str, sport: str) -> str:
    raw = f"{event_type} {description}".lower()

    if sport == Sport.NHL:
        if "goal" in raw:
            return "Goal"
        if "penalty" in raw or "minor" in raw or "major" in raw:
            return "Penalty"
        if "power play" in raw:
            return "Power Play"
        if "empty net" in raw or "goalie pulled" in raw:
            return "Goalie Change"
        if "save" in raw or "stopped" in raw:
            return "Save"

    if sport == Sport.NBA:
        if "technical" in raw:
            return "Technical"
        if "flagrant" in raw:
            return "Flagrant"
        if "ejection" in raw:
            return "Ejection"
        if "timeout" in raw:
            return "Timeout"
        if "turnover" in raw or "steal" in raw or "block" in raw:
            return "Turnover"
        if "review" in raw or "challenge" in raw:
            return "Review"
        if "injury" in raw:
            return "Injury"
        if "makes" in description.lower():
            return "Score"
        if "misses" in description.lower():
            return "Missed Shot"

    if sport == Sport.MLB:
        if "home run" in raw:
            return "Home Run"
        if "pitching change" in raw:
            return "Pitching Change"
        if "mound visit" in raw:
            return "Mound Visit"
        if "error" in raw:
            return "Error"

    if sport == Sport.NFL:
        if "touchdown" in raw:
            return "Touchdown"
        if "interception" in raw or "fumble" in raw or "turnover" in raw:
            return "Turnover"
        if "field goal" in raw:
            return "Field Goal"
        if "penalty" in raw:
            return "Penalty"
        if "timeout" in raw:
            return "Timeout"
        if "injury" in raw:
            return "Injury"
        if "review" in raw or "challenge" in raw:
            return "Review"

    if sport == Sport.SOCCER:
        if "red card" in raw:
            return "Red Card"
        if "yellow card" in raw:
            return "Yellow Card"
        if "goal" in raw:
            return "Goal"
        if "penalty" in raw:
            return "Penalty"
        if "var" in raw or "review" in raw:
            return "VAR Review"
        if "substitution" in raw:
            return "Substitution"

    if sport == Sport.UFC:
        if "knockdown" in raw:
            return "Knockdown"
        if "takedown" in raw:
            return "Takedown"
        if "submission" in raw:
            return "Submission"
        if "doctor" in raw or "injury" in raw:
            return "Doctor Check"

    return event_type


class EspnEventsPoller:
    def __init__(self, queue: asyncio.Queue) -> None:
        self.queue = queue
        self.client = httpx.AsyncClient(timeout=10.0)
        self._watched_games: dict[str, str] = {}
        self._seen_plays: dict[str, set[str]] = {}
        self._status = "disconnected"

    @property
    def status(self) -> str:
        return self._status

    def watch_game(self, espn_id: str, sport: str) -> None:
        self._watched_games[espn_id] = sport
        if espn_id not in self._seen_plays:
            self._seen_plays[espn_id] = set()

    def unwatch_game(self, espn_id: str) -> None:
        self._watched_games.pop(espn_id, None)
        self._seen_plays.pop(espn_id, None)

    async def close(self) -> None:
        await self.client.aclose()

    async def poll_game(self, espn_id: str, sport: str) -> list[dict]:
        sport_path = SPORT_PATHS.get(sport)
        if not sport_path:
            return []

        url = f"{SUMMARY_BASE}/{sport_path}/summary"
        try:
            resp = await self.client.get(url, params={"event": espn_id})
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, Exception):
            logger.exception("espn_events_error", espn_id=espn_id, sport=sport)
            return []

        plays_data = data.get("plays", [])
        if isinstance(plays_data, dict):
            plays_data = plays_data.get("allPlays", []) or plays_data.get("items", [])

        all_events = _extract_events(plays_data, sport, _event_context(data))
        seen = self._seen_plays.get(espn_id, set())
        new_events = []
        for ev in all_events:
            key = f"{ev['event_type']}:{ev['description'][:50]}:{ev.get('clock', '')}"
            if key not in seen:
                seen.add(key)
                ev["espn_id"] = espn_id
                ev["sport"] = sport
                new_events.append(ev)

        self._seen_plays[espn_id] = seen
        return new_events

    async def poll_all(self) -> list[dict]:
        if not self._watched_games:
            return []

        all_new = []
        for espn_id, sport in list(self._watched_games.items()):
            new_events = await self.poll_game(espn_id, sport)
            all_new.extend(new_events)

        self._status = "connected"
        return all_new

    async def _enqueue(self, data: dict) -> None:
        if self.queue.full():
            logger.warning("espn_events_queue_overflow")
        await self.queue.put(data)


async def espn_events_poller(queue: asyncio.Queue) -> None:
    poller = EspnEventsPoller(queue)
    while True:
        try:
            new_events = await poller.poll_all()
            for event in new_events:
                await poller._enqueue(event)
            if new_events:
                logger.info("espn_events_detected", count=len(new_events))
        except Exception:
            logger.exception("espn_events_poll_error")
            poller._status = "error"
        await asyncio.sleep(settings.events_poll_interval_s)
