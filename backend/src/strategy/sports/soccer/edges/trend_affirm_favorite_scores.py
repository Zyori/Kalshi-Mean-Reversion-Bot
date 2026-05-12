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
    """Fires when a goal lands early and the favorite is not now behind.

    Research-mode: with no clear favorite (baseline ~ 0.5) we still fire —
    the trade will be tagged with this edge so analysis can split outcomes
    by whether a clear favorite existed.
    """
    if not is_goal(ctx):
        return None
    if ctx.minute > 60:
        return None
    has_clear_favorite = ctx.baseline_prob >= 0.55
    if has_clear_favorite and favorite_behind(
        home_score=ctx.home_score,
        away_score=ctx.away_score,
        is_home_favorite=ctx.is_home_favorite,
    ):
        return None
    return EdgeSignal(
        signal_kind=SIGNAL_KIND,
        classification="reversion_candidate",
        reason=(
            f"Goal at {ctx.minute}', score {ctx.home_score}-{ctx.away_score} "
            f"(baseline {ctx.baseline_prob:.2f})"
        ),
    )
