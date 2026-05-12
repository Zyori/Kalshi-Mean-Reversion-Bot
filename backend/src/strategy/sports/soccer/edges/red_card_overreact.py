"""Edge: market overshoots after a red card.

Thesis: a red card is a sharp, jarring event that often produces a price
spike the market trims back over the next several minutes. Fade the
immediate move.

Fires only when:
- A red card just landed
- It's not late in the match (≤ 75')
"""

from src.strategy.sports.soccer.context import EdgeContext, EdgeSignal
from src.strategy.sports.soccer.predicates import is_red_card

SIGNAL_KIND = "red_card_overreact"


def evaluate(ctx: EdgeContext) -> EdgeSignal | None:
    if not is_red_card(ctx):
        return None
    if ctx.minute > 75:
        return None
    return EdgeSignal(
        signal_kind=SIGNAL_KIND,
        # Downstream uses `structural_shift` for log-only events. We want
        # the trader to consider this, so classify as reversion_candidate.
        classification="reversion_candidate",
        reason=f"Red card at {ctx.minute}', fade the immediate spike",
    )
