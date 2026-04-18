from typing import Any


class NhlClassifier:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.min_favorite_prob_pp = p.get("min_favorite_prob_pp", 0.60)
        self.min_favorite_prob_es = p.get("min_favorite_prob_es", 0.65)
        self.max_deficit_reversion = p.get("max_deficit_reversion", 2)

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

        deficit = abs(home_score - away_score)
        favorite_behind = (is_home_favorite and home_score < away_score) or (
            not is_home_favorite and away_score < home_score
        )

        if "goalie" in desc_lower and ("pulled" in desc_lower or "empty net" in desc_lower):
            return "structural_shift"

        period_num = _parse_period(period)
        if period_num >= 2 and deficit > self.max_deficit_reversion:
            return "structural_shift"

        if not favorite_behind:
            return "neutral"

        is_pp_goal = "power play" in et_lower or "power play" in desc_lower
        is_goal = "goal" in et_lower or "goal" in desc_lower

        if is_pp_goal and period_num <= 2 and baseline_prob >= self.min_favorite_prob_pp:
            return "reversion_candidate"

        if is_goal and period_num == 1 and baseline_prob >= self.min_favorite_prob_es:
            return "reversion_candidate"

        return "neutral"

    def get_default_params(self) -> dict[str, Any]:
        return {
            "min_favorite_prob_pp": self.min_favorite_prob_pp,
            "min_favorite_prob_es": self.min_favorite_prob_es,
            "max_deficit_reversion": self.max_deficit_reversion,
        }


def _parse_period(period: str) -> int:
    try:
        return int(period)
    except (ValueError, TypeError):
        return 0
