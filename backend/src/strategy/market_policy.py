from typing import Any

from src.config import settings

MARKET_POLICY_ORDER: tuple[str, ...] = (
    "moneyline",
    "spread",
    "total",
    "team_total",
)

MARKET_POLICY_METADATA: dict[str, dict[str, str]] = {
    "moneyline": {
        "source": (
            "Real Kalshi demo moneyline when matched, otherwise "
            "synthetic home-win pricing."
        ),
        "summary": (
            "Trade the opener or matched Kalshi price when a live event "
            "temporarily overstates the favorite's new win probability."
        ),
        "status": "live",
        "status_note": (
            "Actively logging and trading on matched Kalshi demo or "
            "synthetic moneyline rails."
        ),
    },
    "spread": {
        "source": "Synthetic spread rail built from opening spread and live score state.",
        "summary": (
            "Fade temporary cover-margin overshoots back toward the opening "
            "spread when the move is event-driven, not structural."
        ),
        "status": "live",
        "status_note": "Actively logging and trading on synthetic spread rails.",
    },
    "total": {
        "source": (
            "Synthetic game total rail built from opening total and "
            "live pace projection."
        ),
        "summary": (
            "Fade temporary pace shocks back toward the opening total when "
            "scoring bursts or leverage events push projections out of line."
        ),
        "status": "live",
        "status_note": "Actively logging and trading on synthetic game total rails.",
    },
    "team_total": {
        "source": (
            "Synthetic home and away team-total rails built from opening "
            "team totals and live team scoring pace."
        ),
        "summary": (
            "Fade temporary team scoring pace shocks back toward the opening "
            "team total for the home or away side independently."
        ),
        "status": "conditional",
        "status_note": (
            "Implemented end to end, but only active when opening team-total "
            "lines are available from upstream odds data."
        ),
    },
}


def _thresholds_for_market(market_category: str) -> tuple[float, float]:
    if market_category == "moneyline":
        return (
            settings.paper_trade_min_confidence_moneyline,
            settings.paper_trade_min_deviation_moneyline,
        )
    if market_category == "spread":
        return (
            settings.paper_trade_min_confidence_spread,
            settings.paper_trade_min_deviation_spread,
        )
    if market_category in {"total", "team_total"}:
        return (
            settings.paper_trade_min_confidence_total,
            settings.paper_trade_min_deviation_total,
        )
    return (settings.paper_trade_min_confidence, settings.paper_trade_min_deviation)


def get_market_policy() -> dict[str, dict[str, Any]]:
    policy: dict[str, dict[str, Any]] = {}
    for market_category in MARKET_POLICY_ORDER:
        metadata = MARKET_POLICY_METADATA[market_category]
        confidence, deviation = _thresholds_for_market(market_category)
        policy[market_category] = {
            "market_category": market_category,
            "source": metadata["source"],
            "summary": metadata["summary"],
            "status": metadata["status"],
            "status_note": metadata["status_note"],
            "confidence_threshold": confidence,
            "deviation_threshold": deviation,
        }
    return policy


def get_trade_gate_settings() -> dict[str, dict[str, float]]:
    policy = get_market_policy()
    return {
        market_category: {
            "confidence": float(market["confidence_threshold"]),
            "deviation": float(market["deviation_threshold"]),
        }
        for market_category, market in policy.items()
    }
