from collections.abc import Mapping
from typing import Any

from src.config import settings
from src.strategy.classifier import CLASSIFIER_MAP
from src.strategy.market_policy import get_market_policy
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
    market_policy = get_market_policy()
    classifier_params = _classifier_params()

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
                        "summary": str(market_policy["spread"]["summary"]),
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
                        "summary": str(market_policy["total"]["summary"]),
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
                        "summary": str(market_policy["team_total"]["summary"]),
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
            "markets": list(market_policy.values()),
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
