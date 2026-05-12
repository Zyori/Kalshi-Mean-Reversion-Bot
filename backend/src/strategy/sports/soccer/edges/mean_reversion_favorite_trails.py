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
    """Fires when a goal lands while the favorite is currently trailing.

    Research-mode: when baseline_prob is unknown (Kalshi-fallback path
    failed or no Odds API line), we still fire — the dataset will tell
    us whether unbaselined trades are worth keeping. Has-baseline trades
    can be filtered out via paper_trades.game_context later if needed.
    """
    if not is_goal(ctx):
        return None
    if ctx.minute > 75:
        return None
    if score_deficit(ctx.home_score, ctx.away_score) > 2:
        return None
    # When we have a clear favorite, require it to be the one trailing.
    # When we don't (baseline ~ 0.5), still fire — collect the data.
    has_clear_favorite = ctx.baseline_prob >= 0.55
    if has_clear_favorite and not favorite_behind(
        home_score=ctx.home_score,
        away_score=ctx.away_score,
        is_home_favorite=ctx.is_home_favorite,
    ):
        return None
    return EdgeSignal(
        signal_kind=SIGNAL_KIND,
        classification="reversion_candidate",
        reason=(
            f"Goal during {ctx.home_score}-{ctx.away_score} state at {ctx.minute}' "
            f"(baseline {ctx.baseline_prob:.2f})"
        ),
    )
