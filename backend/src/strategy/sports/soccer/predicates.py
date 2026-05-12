"""Pure event-shape predicates shared across soccer edges.

Each predicate answers a single yes/no question about an EdgeContext's
event. Keeping them isolated makes edges read like English: "if it's a
goal and the favorite trails, fire."
"""

from src.strategy.sports.soccer.context import EdgeContext


def is_goal(ctx: EdgeContext) -> bool:
    et = ctx.event_type.lower()
    desc = ctx.description.lower()
    # "no goal" guards against VAR-overturned commentary.
    return ("goal" in et or "goal" in desc) and "no goal" not in desc


def is_red_card(ctx: EdgeContext) -> bool:
    et = ctx.event_type.lower()
    desc = ctx.description.lower()
    return "red card" in et or "red card" in desc or "sent off" in desc


def is_penalty_awarded(ctx: EdgeContext) -> bool:
    """True for a penalty *awarded* (not the resulting goal/miss).
    The conversion itself comes through separately as a goal event."""
    et = ctx.event_type.lower()
    desc = ctx.description.lower()
    if "penalty" not in et and "penalty" not in desc:
        return False
    return "missed" not in desc and "saved" not in desc
