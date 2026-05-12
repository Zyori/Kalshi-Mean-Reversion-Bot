"""Edge: market underprices the favorite's strength after an early goal.

Thesis: when the favorite scores early, Kalshi anchors on pre-game prices
and is slow to fully update for the new state. Ride the move.

Fires only when:
- A goal just landed
- Pre-game favorite was clear (baseline ≥ 0.55)
- It's early enough that meaningful price movement is still ahead (≤ 60')
- The favorite is now ahead or level (so the goal-scorer is the favorite,
  not the underdog clawing back)
"""

from src.strategy.sports.common import favorite_behind
from src.strategy.sports.soccer.context import EdgeContext, EdgeSignal
from src.strategy.sports.soccer.predicates import is_goal

SIGNAL_KIND = "trend_affirm_favorite_scores"


def evaluate(ctx: EdgeContext) -> EdgeSignal | None:
    if not is_goal(ctx):
        return None
    if ctx.baseline_prob < 0.55:
        return None
    if ctx.minute > 60:
        return None
    favorite_still_behind = favorite_behind(
        home_score=ctx.home_score,
        away_score=ctx.away_score,
        is_home_favorite=ctx.is_home_favorite,
    )
    if favorite_still_behind:
        return None
    return EdgeSignal(
        signal_kind=SIGNAL_KIND,
        classification="reversion_candidate",
        reason=(
            f"Favorite (baseline {ctx.baseline_prob:.2f}) up or level "
            f"{ctx.home_score}-{ctx.away_score} after early goal at {ctx.minute}'"
        ),
    )
