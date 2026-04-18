from typing import Any


class SoccerClassifier:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.min_favorite_prob = p.get("min_favorite_prob", 0.60)

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

        favorite_behind = (is_home_favorite and home_score < away_score) or (
            not is_home_favorite and away_score < home_score
        )

        minute = _parse_minute(period)
        is_goal = "goal" in et_lower or "goal" in desc_lower

        if is_goal and favorite_behind and minute <= 70 and baseline_prob >= self.min_favorite_prob:
            return "reversion_candidate"

        return "neutral"

    def get_default_params(self) -> dict[str, Any]:
        return {"min_favorite_prob": self.min_favorite_prob}


def _parse_minute(period: str) -> int:
    try:
        return int(period)
    except (ValueError, TypeError):
        return 90
