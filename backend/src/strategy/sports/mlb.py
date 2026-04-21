from typing import Any

from src.strategy.sports.common import favorite_behind, score_deficit


class MlbClassifier:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.min_favorite_prob = p.get("min_favorite_prob", 0.56)
        self.max_deficit_reversion = p.get("max_deficit_reversion", 3)
        self.max_early_deficit = p.get("max_early_deficit", 4)

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
        deficit = score_deficit(home_score, away_score)
        inning = _parse_inning(period)
        favorite_is_behind = favorite_behind(
            home_score=home_score,
            away_score=away_score,
            is_home_favorite=is_home_favorite,
        )

        if inning >= 7 and deficit > self.max_deficit_reversion:
            return "structural_shift"

        is_hr = "home run" in event_type.lower() or "home run" in description.lower()
        scoring_swing = any(
            token in (event_type.lower() + " " + description.lower())
            for token in ("home run", "double", "triple", "single", "walk", "hit by pitch")
        )

        if is_hr and favorite_is_behind and inning <= 6 and baseline_prob >= self.min_favorite_prob:
            return "reversion_candidate"

        if (
            favorite_is_behind
            and inning <= 5
            and deficit <= self.max_early_deficit
            and baseline_prob >= self.min_favorite_prob
            and (scoring_swing or deficit >= 1)
        ):
            return "reversion_candidate"

        return "neutral"

    def get_default_params(self) -> dict[str, Any]:
        return {
            "min_favorite_prob": self.min_favorite_prob,
            "max_deficit_reversion": self.max_deficit_reversion,
            "max_early_deficit": self.max_early_deficit,
        }


def _parse_inning(period: str) -> int:
    try:
        return int(period)
    except (ValueError, TypeError):
        return 0
