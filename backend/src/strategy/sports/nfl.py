from typing import Any


class NflClassifier:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.min_favorite_prob = p.get("min_favorite_prob", 0.65)
        self.max_deficit_reversion = p.get("max_deficit_reversion", 14)

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
        quarter = _parse_quarter(period)
        favorite_behind = (is_home_favorite and home_score < away_score) or (
            not is_home_favorite and away_score < home_score
        )

        if quarter >= 4 and deficit > self.max_deficit_reversion:
            return "structural_shift"

        et_lower = event_type.lower()
        is_td = "touchdown" in et_lower or "touchdown" in description.lower()
        is_turnover = any(k in et_lower for k in ("turnover", "interception", "fumble"))

        if (
            (is_td or is_turnover)
            and favorite_behind
            and quarter <= 3
            and baseline_prob >= self.min_favorite_prob
        ):
            return "reversion_candidate"

        return "neutral"

    def get_default_params(self) -> dict[str, Any]:
        return {
            "min_favorite_prob": self.min_favorite_prob,
            "max_deficit_reversion": self.max_deficit_reversion,
        }


def _parse_quarter(period: str) -> int:
    try:
        return int(period)
    except (ValueError, TypeError):
        return 0
