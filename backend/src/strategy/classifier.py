from typing import Any

from src.core.logging import get_logger
from src.core.types import Sport
from src.strategy.sports.mlb import MlbClassifier
from src.strategy.sports.nba import NbaClassifier
from src.strategy.sports.nfl import NflClassifier
from src.strategy.sports.nhl import NhlClassifier
from src.strategy.sports.soccer import SoccerClassifier
from src.strategy.sports.ufc import UfcClassifier

logger = get_logger(__name__)

CLASSIFIER_MAP: dict[str, type] = {
    Sport.NHL: NhlClassifier,
    Sport.NBA: NbaClassifier,
    Sport.MLB: MlbClassifier,
    Sport.NFL: NflClassifier,
    Sport.SOCCER: SoccerClassifier,
    Sport.UFC: UfcClassifier,
}


class EventClassifier:
    def __init__(self, params: dict[str, dict[str, Any]] | None = None) -> None:
        sport_params = params or {}
        self._classifiers = {
            sport: cls(sport_params.get(sport, {})) for sport, cls in CLASSIFIER_MAP.items()
        }

    def classify(
        self,
        sport: str,
        event_type: str,
        description: str,
        home_score: int,
        away_score: int,
        period: str,
        baseline_prob: float,
        is_home_favorite: bool,
    ) -> str:
        classifier = self._classifiers.get(sport)
        if not classifier:
            logger.warning("no_classifier", sport=sport)
            return "neutral"

        return classifier.classify_event(
            event_type=event_type,
            description=description,
            home_score=home_score,
            away_score=away_score,
            period=period,
            baseline_prob=baseline_prob,
            is_home_favorite=is_home_favorite,
        )
