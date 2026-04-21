from typing import Any

from src.strategy.sports.common import favorite_behind, score_deficit


class NflClassifier:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.min_favorite_prob = p.get("min_favorite_prob", 0.60)
        self.max_deficit_reversion = p.get("max_deficit_reversion", 14)
        self.max_early_deficit = p.get("max_early_deficit", 10)

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
        quarter = _parse_quarter(period)
        favorite_is_behind = favorite_behind(
            home_score=home_score,
            away_score=away_score,
            is_home_favorite=is_home_favorite,
        )

        if quarter >= 4 and deficit > self.max_deficit_reversion:
            return "structural_shift"

        et_lower = event_type.lower()
        is_td = "touchdown" in et_lower or "touchdown" in description.lower()
        is_turnover = any(k in et_lower for k in ("turnover", "interception", "fumble"))

        if (
            (is_td or is_turnover)
            and favorite_is_behind
            and quarter <= 3
            and baseline_prob >= self.min_favorite_prob
        ):
            return "reversion_candidate"

        if (
            favorite_is_behind
            and quarter <= 2
            and deficit <= self.max_early_deficit
            and baseline_prob >= self.min_favorite_prob
            and deficit >= 3
        ):
            return "reversion_candidate"

        return "neutral"

    def get_default_params(self) -> dict[str, Any]:
        return {
            "min_favorite_prob": self.min_favorite_prob,
            "max_deficit_reversion": self.max_deficit_reversion,
            "max_early_deficit": self.max_early_deficit,
        }


def _parse_quarter(period: str) -> int:
    try:
        return int(period)
    except (ValueError, TypeError):
        return 0
