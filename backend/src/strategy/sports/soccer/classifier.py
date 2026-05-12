"""Soccer classifier shell.

Walks the SOCCER_EDGES registry in priority order and returns the first
firing signal. Exposes `evaluate(ctx)` for callers that want the full
EdgeSignal (signal_kind, classification, reason) and `classify_event(...)`
for the legacy interface that just wants the classification string.
"""

from typing import Any

from src.strategy.sports.soccer.context import EdgeContext, EdgeSignal
from src.strategy.sports.soccer.registry import SOCCER_EDGES


class SoccerClassifier:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        # Params reserved for future config-driven thresholds. Today the
        # edges keep their own thresholds inline; we'll surface them
        # through config_params once we have data to support tuning.
        _ = params or {}

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
        ctx = EdgeContext(
            event_type=event_type,
            description=description,
            home_score=home_score,
            away_score=away_score,
            minute=_parse_minute(period),
            baseline_prob=baseline_prob,
            is_home_favorite=is_home_favorite,
        )
        signal = self.evaluate(ctx)
        return signal.classification if signal else "neutral"

    def evaluate(self, ctx: EdgeContext) -> EdgeSignal | None:
        for edge in SOCCER_EDGES:
            signal = edge(ctx)
            if signal is not None:
                return signal
        return None

    def get_default_params(self) -> dict[str, Any]:
        return {}


def _parse_minute(period: str) -> int:
    try:
        return int(period)
    except (ValueError, TypeError):
        return 90
