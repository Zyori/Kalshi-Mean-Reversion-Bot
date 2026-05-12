"""Edge: market overreacts when the pre-game favorite goes behind.

Thesis: when the favorite concedes, the Kalshi price drops further than
the true probability shift warrants. We fade that drop and bet the
favorite back to recover.

Fires only when:
- A goal just landed
- The pre-game favorite was clear (baseline ≥ 0.55)
- The favorite is currently behind
- The deficit is recoverable (≤ 2 goals)
- It's not late in the match (≤ 75')
"""

from src.strategy.sports.common import favorite_behind, score_deficit
from src.strategy.sports.soccer.context import EdgeContext, EdgeSignal
from src.strategy.sports.soccer.predicates import is_goal

SIGNAL_KIND = "mean_reversion_favorite_trails"


def evaluate(ctx: EdgeContext) -> EdgeSignal | None:
    if not is_goal(ctx):
        return None
    if ctx.baseline_prob < 0.55:
        return None
    if not favorite_behind(
        home_score=ctx.home_score,
        away_score=ctx.away_score,
        is_home_favorite=ctx.is_home_favorite,
    ):
        return None
    if score_deficit(ctx.home_score, ctx.away_score) > 2:
        return None
    if ctx.minute > 75:
        return None
    return EdgeSignal(
        signal_kind=SIGNAL_KIND,
        classification="reversion_candidate",
        reason=(
            f"Favorite (baseline {ctx.baseline_prob:.2f}) trailing "
            f"{ctx.home_score}-{ctx.away_score} at {ctx.minute}'"
        ),
    )
