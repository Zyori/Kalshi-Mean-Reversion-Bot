"""Registry-level test: when multiple edges could fire for the same event,
the priority order in registry.py determines which wins."""

from src.strategy.sports.soccer.classifier import SoccerClassifier
from src.strategy.sports.soccer.context import EdgeContext


def test_red_card_takes_priority_when_description_also_mentions_goal():
    # A red-card commentary line sometimes mentions "goalkeeper" or similar
    # — the high-priority edge should still win the tag, not get masked by
    # the goal predicate.
    clf = SoccerClassifier()
    s = clf.evaluate(
        EdgeContext(
            event_type="Red Card",
            description="Straight red to the goalkeeper",
            home_score=0,
            away_score=0,
            minute=30,
            baseline_prob=0.6,
            is_home_favorite=True,
        )
    )
    assert s is not None
    assert s.signal_kind == "red_card_overreact"


def test_classify_event_returns_neutral_when_no_edge_fires():
    clf = SoccerClassifier()
    label = clf.classify_event(
        event_type="Substitution",
        description="Routine substitution at the break",
        home_score=1,
        away_score=1,
        period="46",
        baseline_prob=0.6,
        is_home_favorite=True,
    )
    assert label == "neutral"
