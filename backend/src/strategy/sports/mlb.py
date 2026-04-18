from typing import Any


class MlbClassifier:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.min_favorite_prob = p.get("min_favorite_prob", 0.60)
        self.max_deficit_reversion = p.get("max_deficit_reversion", 3)

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
        deficit = abs(home_score - away_score)
        inning = _parse_inning(period)
        favorite_behind = (is_home_favorite and home_score < away_score) or (
            not is_home_favorite and away_score < home_score
        )

        if inning >= 7 and deficit > self.max_deficit_reversion:
            return "structural_shift"

        is_hr = "home run" in event_type.lower() or "home run" in description.lower()

        if is_hr and favorite_behind and inning <= 6 and baseline_prob >= self.min_favorite_prob:
            return "reversion_candidate"

        if favorite_behind and inning <= 5 and baseline_prob >= self.min_favorite_prob:
            return "reversion_candidate"

        return "neutral"

    def get_default_params(self) -> dict[str, Any]:
        return {
            "min_favorite_prob": self.min_favorite_prob,
            "max_deficit_reversion": self.max_deficit_reversion,
        }


def _parse_inning(period: str) -> int:
    try:
        return int(period)
    except (ValueError, TypeError):
        return 0
