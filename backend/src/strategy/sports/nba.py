from typing import Any

from src.strategy.sports.common import favorite_behind, score_deficit


class NbaClassifier:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.min_favorite_prob = p.get("min_favorite_prob", 0.60)
        self.max_deficit_reversion = p.get("max_deficit_reversion", 15)
        self.max_early_deficit = p.get("max_early_deficit", 12)

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
        period_num = _parse_period(period)
        favorite_is_behind = favorite_behind(
            home_score=home_score,
            away_score=away_score,
            is_home_favorite=is_home_favorite,
        )
        event_text = f"{event_type.lower()} {description.lower()}"
        high_leverage_event = any(token in event_text for token in (
            "timeout",
            "technical",
            "flagrant",
            "turnover",
            "steal",
        ))

        if period_num >= 3 and deficit > self.max_deficit_reversion:
            return "structural_shift"

        if (
            favorite_is_behind
            and period_num <= 2
            and deficit <= self.max_early_deficit
            and baseline_prob >= self.min_favorite_prob
            and (deficit >= 4 or high_leverage_event)
        ):
            return "reversion_candidate"

        return "neutral"

    def get_default_params(self) -> dict[str, Any]:
        return {
            "min_favorite_prob": self.min_favorite_prob,
            "max_deficit_reversion": self.max_deficit_reversion,
            "max_early_deficit": self.max_early_deficit,
        }


def _parse_period(period: str) -> int:
    try:
        return int(period)
    except (ValueError, TypeError):
        return 0
