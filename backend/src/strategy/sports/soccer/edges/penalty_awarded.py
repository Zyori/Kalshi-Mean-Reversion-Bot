"""Edge: market price moves sharply when a penalty is awarded.

Thesis: a penalty awarded is a high-probability scoring chance the market
adjusts to immediately. Bet the team that drew it — momentum + likely
goal coming.

Fires only when:
- A penalty was just awarded (not missed/saved)
- It's not very late in the match (≤ 80')
"""

from src.strategy.sports.soccer.context import EdgeContext, EdgeSignal
from src.strategy.sports.soccer.predicates import is_penalty_awarded

SIGNAL_KIND = "penalty_awarded"


def evaluate(ctx: EdgeContext) -> EdgeSignal | None:
    if not is_penalty_awarded(ctx):
        return None
    if ctx.minute > 80:
        return None
    return EdgeSignal(
        signal_kind=SIGNAL_KIND,
        classification="reversion_candidate",
        reason=f"Penalty awarded at {ctx.minute}'",
    )
