from typing import Any, Protocol


class SportClassifier(Protocol):
    def classify_event(
        self,
        event_type: str,
        description: str,
        home_score: int,
        away_score: int,
        period: str,
        baseline_prob: float,
        is_home_favorite: bool,
    ) -> str: ...

    def get_default_params(self) -> dict[str, Any]: ...
