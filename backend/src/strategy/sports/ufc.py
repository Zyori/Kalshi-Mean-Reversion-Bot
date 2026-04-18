from typing import Any


class UfcClassifier:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        p = params or {}
        self.min_favorite_prob = p.get("min_favorite_prob", 0.70)

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
        # UFC scoring is round-based; significant upsets happen when
        # the underdog wins early rounds decisively
        return "neutral"

    def get_default_params(self) -> dict[str, Any]:
        return {"min_favorite_prob": self.min_favorite_prob}
