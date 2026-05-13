"""Tiny stats helpers shared by analyzers.

Wilson confidence interval is used instead of the naive normal
approximation because we're working with small samples (10-100 trades)
where the simple formula gives interval bounds outside [0, 1] and
underestimates uncertainty at the extremes.
"""

from __future__ import annotations

import math


def wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Return (low, high) bounds of the Wilson 95% CI for win rate.

    Returns (0.0, 1.0) when n == 0 — caller should check sample size before
    drawing conclusions from a maximally-wide interval."""
    if n == 0:
        return (0.0, 1.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def expected_value_per_trade(
    win_rate: float, avg_win_payoff_cents: int, avg_loss_cents: int
) -> float:
    """Crude EV per trade in cents. Assumes losses are -avg_loss_cents.
    Useful as a "would a flat-bet on this edge make money?" check."""
    return win_rate * avg_win_payoff_cents - (1 - win_rate) * avg_loss_cents
