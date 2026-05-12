"""Shared builders for soccer-edge tests."""

from src.strategy.sports.soccer.context import EdgeContext


def ctx(
    *,
    event_type: str = "Goal",
    description: str = "",
    home_score: int = 0,
    away_score: int = 0,
    minute: int = 30,
    baseline_prob: float = 0.6,
    is_home_favorite: bool = True,
) -> EdgeContext:
    return EdgeContext(
        event_type=event_type,
        description=description,
        home_score=home_score,
        away_score=away_score,
        minute=minute,
        baseline_prob=baseline_prob,
        is_home_favorite=is_home_favorite,
    )
