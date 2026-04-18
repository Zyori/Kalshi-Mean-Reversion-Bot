from typing import Protocol


class ProbabilityEstimator(Protocol):
    def estimate(self, score: float, context: dict) -> float: ...


class ConservativeEstimator:
    def estimate(self, score: float, context: dict) -> float:
        raw_edge = score * 0.20
        shrinkage = 0.5
        return 0.50 + raw_edge * shrinkage


def kelly_fraction(p: float, entry_price_cents: int) -> float:
    if entry_price_cents <= 0 or entry_price_cents >= 100:
        return 0.0
    b = (100 - entry_price_cents) / entry_price_cents
    f = (b * p - (1 - p)) / b
    return max(0.0, f)


def kelly_size(
    p: float,
    entry_price_cents: int,
    bankroll_cents: int,
    pending_wagers_cents: int,
    fraction_multiplier: float = 0.25,
    min_bet: int = 100,
    max_bet: int = 2500,
) -> int:
    f = kelly_fraction(p, entry_price_cents)
    if f <= 0:
        return 0
    available = bankroll_cents - pending_wagers_cents
    if available <= 0:
        return 0
    size = int(f * fraction_multiplier * available)
    if size < min_bet:
        return 0
    return min(size, max_bet)
