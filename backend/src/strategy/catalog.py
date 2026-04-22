from collections.abc import Mapping
from typing import Any

from src.config import settings
from src.services.trade_policy_service import get_trade_gate_settings
from src.strategy.classifier import CLASSIFIER_MAP
from src.strategy.sports.common import (
    HIGH_LEVERAGE_EVENT_TOKENS,
    SCORING_EVENT_TOKENS,
    SPORT_SEGMENTS,
    SPREAD_CANDIDATE_EDGES,
    SPREAD_STRUCTURAL_EDGES,
    STRUCTURAL_EVENT_TOKENS,
    TEAM_TOTAL_CANDIDATE_EDGES,
    TEAM_TOTAL_STRUCTURAL_EDGES,
    TOTAL_CANDIDATE_EDGES,
    TOTAL_STRUCTURAL_EDGES,
)

SPORT_DISPLAY_NAMES: dict[str, str] = {
    "nhl": "NHL",
    "nba": "NBA",
    "mlb": "MLB",
    "nfl": "NFL",
    "soccer": "Soccer",
    "ufc": "UFC",
}

SPORT_SUMMARIES: dict[str, str] = {
    "nhl": (
        "Early special-teams goals and one-goal swings matter most; "
        "late pulled-goalie states are treated as structural."
    ),
    "nba": (
        "Fast runs, turnovers, and timeout sequences create the cleanest "
        "mean-reversion setups before late blowouts harden."
    ),
    "mlb": (
        "The opener stays sticky through the middle innings, but late "
        "multi-run gaps shift the game into structural territory."
    ),
    "nfl": (
        "Touchdowns and turnovers through Q3 create the best reversion "
        "windows; late two-score gaps are treated more cautiously."
    ),
    "soccer": (
        "Goals move the market hardest, but red cards and other "
        "man-advantage states are treated as structural breaks."
    ),
    "ufc": (
        "Tracked primarily for collection right now; live trading stays "
        "conservative until richer round-level signals are added."
    ),
}

MONEYLINE_SUMMARIES: dict[str, str] = {
    "nhl": (
        "Back strong favorites that fall behind on early goals or power-play "
        "swings before the game state becomes structurally late."
    ),
    "nba": (
        "Back stronger pregame sides when early and mid-game runs overshoot "
        "the opening win baseline."
    ),
    "mlb": (
        "Back the opener when early inning scoring swings temporarily push "
        "a favorite too far off its starting win probability."
    ),
    "nfl": (
        "Back stronger pregame sides after touchdowns or turnovers create "
        "temporary win-probability overshoots."
    ),
    "soccer": (
        "Back favorites after early goals against them, but stop treating "
        "the move as reversion once cards or late clocks change structure."
    ),
    "ufc": (
        "Moneyline rules remain conservative and observational until "
        "round-level scoring signals are upgraded."
    ),
}

MARKET_SUMMARIES: dict[str, str] = {
    "spread": (
        "Fade temporary cover-margin overshoots back toward the opening "
        "spread when the move is event-driven, not structural."
    ),
    "total": (
        "Fade temporary pace shocks back toward the opening total when "
        "scoring bursts or leverage events push projections out of line."
    ),
    "team_total": (
        "Fade temporary team scoring pace shocks back toward the opening "
        "team total for the home or away side independently."
    ),
}

MARKET_SOURCES: dict[str, str] = {
    "moneyline": "Real Kalshi demo moneyline when matched, otherwise synthetic home-win pricing.",
    "spread": "Synthetic spread rail built from opening spread and live score state.",
    "total": "Synthetic game total rail built from opening total and live pace projection.",
    "team_total": (
        "Synthetic home and away team-total rails built from opening "
        "team totals and live team scoring pace."
    ),
}


def _classifier_params() -> dict[str, dict[str, Any]]:
    params: dict[str, dict[str, Any]] = {}
    for sport, classifier_cls in CLASSIFIER_MAP.items():
        classifier = classifier_cls({})
        getter = getattr(classifier, "get_default_params", None)
        params[sport] = getter() if callable(getter) else {}
    return params


def _band_payload(
    candidate_edges: Mapping[str, tuple[float, float]],
    structural_edges: Mapping[str, float],
    sport: str,
) -> dict[str, float] | None:
    candidate = candidate_edges.get(sport)
    structural = structural_edges.get(sport)
    if candidate is None or structural is None:
        return None
    return {
        "candidate_edge_min": float(candidate[0]),
        "candidate_edge_max": float(candidate[1]),
        "structural_edge": float(structural),
    }


def get_strategy_catalog() -> dict[str, Any]:
    gate_settings = get_trade_gate_settings()
    classifier_params = _classifier_params()
    market_policy = [
        {
            "market_category": "moneyline",
            "source": MARKET_SOURCES["moneyline"],
            "summary": (
                "Trade the opener or matched Kalshi price when a live event "
                "temporarily overstates the favorite's new win probability."
            ),
            "confidence_threshold": gate_settings["moneyline"]["confidence"],
            "deviation_threshold": gate_settings["moneyline"]["deviation"],
        },
        {
            "market_category": "spread",
            "source": MARKET_SOURCES["spread"],
            "summary": MARKET_SUMMARIES["spread"],
            "confidence_threshold": gate_settings["spread"]["confidence"],
            "deviation_threshold": gate_settings["spread"]["deviation"],
        },
        {
            "market_category": "total",
            "source": MARKET_SOURCES["total"],
            "summary": MARKET_SUMMARIES["total"],
            "confidence_threshold": gate_settings["total"]["confidence"],
            "deviation_threshold": gate_settings["total"]["deviation"],
        },
        {
            "market_category": "team_total",
            "source": MARKET_SOURCES["team_total"],
            "summary": MARKET_SUMMARIES["team_total"],
            "confidence_threshold": gate_settings["team_total"]["confidence"],
            "deviation_threshold": gate_settings["team_total"]["deviation"],
        },
    ]

    sports = []
    for sport in SPORT_DISPLAY_NAMES:
        sports.append(
            {
                "sport": sport,
                "display_name": SPORT_DISPLAY_NAMES[sport],
                "segments": SPORT_SEGMENTS[sport],
                "summary": SPORT_SUMMARIES[sport],
                "moneyline": {
                    "summary": MONEYLINE_SUMMARIES[sport],
                    "params": classifier_params.get(sport, {}),
                },
                "markets": [
                    {
                        "market_category": "spread",
                        "summary": MARKET_SUMMARIES["spread"],
                        **(
                            _band_payload(
                                SPREAD_CANDIDATE_EDGES,
                                SPREAD_STRUCTURAL_EDGES,
                                sport,
                            )
                            or {}
                        ),
                    },
                    {
                        "market_category": "total",
                        "summary": MARKET_SUMMARIES["total"],
                        **(
                            _band_payload(
                                TOTAL_CANDIDATE_EDGES,
                                TOTAL_STRUCTURAL_EDGES,
                                sport,
                            )
                            or {}
                        ),
                    },
                    {
                        "market_category": "team_total",
                        "summary": MARKET_SUMMARIES["team_total"],
                        **(
                            _band_payload(
                                TEAM_TOTAL_CANDIDATE_EDGES,
                                TEAM_TOTAL_STRUCTURAL_EDGES,
                                sport,
                            )
                            or {}
                        ),
                    },
                ],
            }
        )

    return {
        "platform_timezone": "America/New_York",
        "collection": {
            "schedule_poll_interval_s": settings.odds_poll_interval_s,
            "pregame_poll_interval_s": settings.scoreboard_pregame_poll_interval_s,
            "live_scoreboard_poll_interval_s": settings.scoreboard_live_poll_interval_s,
            "live_events_poll_interval_s": settings.events_poll_interval_s,
            "note": (
                "Schedule and opening lines refresh sparsely; live games are "
                "polled aggressively only once they are active."
            ),
        },
        "trade_policy": {
            "paper_bankroll_start_cents": settings.paper_bankroll_start_cents,
            "max_open_per_market": settings.paper_trade_max_open_per_market,
            "reentry_min_price_move_cents": settings.paper_trade_reentry_min_price_move_cents,
            "markets": market_policy,
            "notes": [
                (
                    "Synthetic spread, total, and team-total rails only "
                    "activate when opening lines are captured."
                ),
                "Team totals inherit the same gate thresholds as totals.",
                "Multiple entries on the same market are allowed when price meaningfully moves.",
            ],
        },
        "event_filters": {
            "scoring_tokens": list(SCORING_EVENT_TOKENS),
            "high_leverage_tokens": list(HIGH_LEVERAGE_EVENT_TOKENS),
            "structural_shift_tokens": list(STRUCTURAL_EVENT_TOKENS),
        },
        "sports": sports,
    }
