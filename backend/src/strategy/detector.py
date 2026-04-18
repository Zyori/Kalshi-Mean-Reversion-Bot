import asyncio
from typing import Any

from src.core.logging import get_logger
from src.strategy.classifier import EventClassifier
from src.strategy.scorer import score_opportunity

logger = get_logger(__name__)


class EventDetector:
    def __init__(
        self,
        espn_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        classifier: EventClassifier | None = None,
    ) -> None:
        self.espn_queue = espn_queue
        self.output_queue = output_queue
        self.classifier = classifier or EventClassifier()
        self._baselines: dict[str, float] = {}

    def set_baseline(self, espn_id: str, prob: float) -> None:
        self._baselines[espn_id] = prob

    async def process_event(self, event: dict[str, Any]) -> dict[str, Any] | None:
        sport = event.get("sport", "")
        espn_id = event.get("espn_id", "")
        event_type = event.get("event_type", "")
        description = event.get("description", "")
        home_score = event.get("home_score", 0)
        away_score = event.get("away_score", 0)
        period = event.get("period", "")
        kalshi_price = event.get("kalshi_price_at")

        baseline = self._baselines.get(espn_id, 0.5)
        is_home_favorite = baseline >= 0.5

        classification = self.classifier.classify(
            sport=sport,
            event_type=event_type,
            description=description,
            home_score=home_score,
            away_score=away_score,
            period=period,
            baseline_prob=baseline,
            is_home_favorite=is_home_favorite,
        )

        event["classification"] = classification
        event["baseline_prob"] = baseline

        if classification == "reversion_candidate" and kalshi_price is not None:
            kalshi_prob = kalshi_price / 100.0
            deviation = abs(baseline - kalshi_prob)
            time_remaining = _estimate_time_remaining(sport, period)

            confidence = score_opportunity(deviation, time_remaining)
            event["confidence_score"] = confidence
            event["deviation"] = deviation

            logger.info(
                "reversion_candidate_detected",
                sport=sport,
                espn_id=espn_id,
                deviation=round(deviation, 4),
                confidence=confidence,
                event_type=event_type,
            )
            return event

        if classification == "structural_shift":
            logger.info(
                "structural_shift_detected",
                sport=sport,
                espn_id=espn_id,
                event_type=event_type,
            )

        return None

    async def run(self) -> None:
        while True:
            event = await self.espn_queue.get()
            result = await self.process_event(event)
            if result:
                if self.output_queue.full():
                    logger.warning("detector_output_queue_full")
                await self.output_queue.put(result)


def _estimate_time_remaining(sport: str, period: str) -> float:
    try:
        p = int(period)
    except (ValueError, TypeError):
        return 0.5

    sport_periods: dict[str, int] = {
        "nhl": 3,
        "nba": 4,
        "mlb": 9,
        "nfl": 4,
        "soccer": 2,
        "ufc": 3,
    }
    total = sport_periods.get(sport, 4)
    return max(0.0, min(1.0, 1.0 - (p / total)))
