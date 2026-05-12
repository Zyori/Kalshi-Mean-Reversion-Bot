"""Ordered registry of soccer edges. Order = priority: the first edge that
fires for a given event wins. To add a new edge, write it in
soccer/edges/<name>.py and append it here.
"""

from collections.abc import Callable

from src.strategy.sports.soccer.context import EdgeContext, EdgeSignal
from src.strategy.sports.soccer.edges import (
    mean_reversion_favorite_trails,
    penalty_awarded,
    red_card_overreact,
    trend_affirm_favorite_scores,
)

Edge = Callable[[EdgeContext], EdgeSignal | None]

SOCCER_EDGES: tuple[Edge, ...] = (
    # High-signal, low-frequency events take priority so they don't get
    # masked by a coincident goal triggering a different edge.
    red_card_overreact.evaluate,
    penalty_awarded.evaluate,
    # Then the goal-driven edges. Mean-reversion goes first because when
    # both could match (an underdog goal that makes the favorite trail),
    # the fade-the-drop bet is the cleaner test of the original thesis.
    mean_reversion_favorite_trails.evaluate,
    trend_affirm_favorite_scores.evaluate,
)
