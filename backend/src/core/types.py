from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator


def _validate_cents(v: int) -> int:
    if not isinstance(v, int):
        raise TypeError("Cents must be an integer")
    if v < 0:
        raise ValueError("Cents cannot be negative")
    return v


def _validate_probability(v: float) -> float:
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"Probability must be between 0 and 1, got {v}")
    return v


Cents = Annotated[int, AfterValidator(_validate_cents)]
Probability = Annotated[float, AfterValidator(_validate_probability)]


class Sport(StrEnum):
    NHL = "nhl"
    NBA = "nba"
    MLB = "mlb"
    NFL = "nfl"
    SOCCER = "soccer"
    UFC = "ufc"


class EventClassification(StrEnum):
    REVERSION_CANDIDATE = "reversion_candidate"
    STRUCTURAL_SHIFT = "structural_shift"
    NEUTRAL = "neutral"


class TradeStatus(StrEnum):
    OPEN = "open"
    RESOLVED_WIN = "resolved_win"
    RESOLVED_LOSS = "resolved_loss"
    RESOLVED_PUSH = "resolved_push"
    SETTLED_EARLY = "settled_early"
    UNRESOLVED = "unresolved"


class InsightType(StrEnum):
    EDGE_VALIDATED = "edge_validated"
    EDGE_DEGRADED = "edge_degraded"
    PARAMETER_RECOMMENDATION = "parameter_recommendation"
    ANOMALY_DETECTED = "anomaly_detected"


class InsightStatus(StrEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"


class GameStatus(StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    HALFTIME = "halftime"
    FINAL = "final"
    POSTPONED = "postponed"


class KalshiEnvironment(StrEnum):
    DEMO = "demo"
    PRODUCTION = "production"


class MarketCategory(StrEnum):
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTAL = "total"
    TEAM_TOTAL = "team_total"


KALSHI_URLS = {
    KalshiEnvironment.DEMO: {
        "rest": "https://demo-api.kalshi.co/trade-api/v2",
        "ws": "wss://demo-api.kalshi.co/trade-api/ws/v2",
    },
    KalshiEnvironment.PRODUCTION: {
        "rest": "https://api.elections.kalshi.com/trade-api/v2",
        "ws": "wss://api.elections.kalshi.com/trade-api/ws/v2",
    },
}
