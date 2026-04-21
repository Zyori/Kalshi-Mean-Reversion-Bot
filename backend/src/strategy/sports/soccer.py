from typing import Any

from src.strategy.sports.common import favorite_behind, score_deficit


class SoccerClassifier:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.min_favorite_prob = p.get("min_favorite_prob", 0.56)
        self.max_reversion_minute = p.get("max_reversion_minute", 75)

    def classify_event(
        self,
        event_type: str,
        description: str,
        home_score: int,
        away_score: int,
        period: str,
        baseline_prob: float,
        is_home_favorite: bool,
    ) -> str:
        et_lower = event_type.lower()
        desc_lower = description.lower()

        if "red card" in et_lower or "red card" in desc_lower:
            return "structural_shift"

        favorite_is_behind = favorite_behind(
            home_score=home_score,
            away_score=away_score,
            is_home_favorite=is_home_favorite,
        )

        minute = _parse_minute(period)
        is_goal = "goal" in et_lower or "goal" in desc_lower
        deficit = score_deficit(home_score, away_score)

        if (
            is_goal
            and favorite_is_behind
            and minute <= self.max_reversion_minute
            and deficit <= 2
            and baseline_prob >= self.min_favorite_prob
        ):
            return "reversion_candidate"

        if (
            favorite_is_behind
            and minute <= 35
            and deficit == 1
            and baseline_prob >= self.min_favorite_prob
        ):
            return "reversion_candidate"

        return "neutral"

    def get_default_params(self) -> dict[str, Any]:
        return {
            "min_favorite_prob": self.min_favorite_prob,
            "max_reversion_minute": self.max_reversion_minute,
        }


def _parse_minute(period: str) -> int:
    try:
        return int(period)
    except (ValueError, TypeError):
        return 90
