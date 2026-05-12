from src.strategy.sports.soccer.edges import trend_affirm_favorite_scores

from .conftest import ctx


def test_fires_when_favorite_takes_early_lead():
    s = trend_affirm_favorite_scores.evaluate(
        ctx(
            event_type="Goal",
            home_score=1,
            away_score=0,
            minute=15,
            baseline_prob=0.6,
            is_home_favorite=True,
        ),
    )
    assert s is not None
    assert s.signal_kind == "trend_affirm_favorite_scores"


def test_silent_when_favorite_still_behind_after_event():
    # Two-goal hole closed to one; favorite still behind. trend_affirm only
    # fires when the favorite is no longer trailing — otherwise it's a
    # mean_reversion situation, not a trend-affirm one.
    s = trend_affirm_favorite_scores.evaluate(
        ctx(
            event_type="Goal",
            home_score=1,
            away_score=2,
            minute=30,
            baseline_prob=0.6,
            is_home_favorite=True,
        ),
    )
    assert s is None


def test_silent_late_in_first_half_onwards():
    # >60' is too late for "early" goal thesis.
    s = trend_affirm_favorite_scores.evaluate(
        ctx(
            event_type="Goal",
            home_score=1,
            away_score=0,
            minute=70,
            baseline_prob=0.6,
            is_home_favorite=True,
        ),
    )
    assert s is None


def test_silent_when_no_clear_favorite():
    s = trend_affirm_favorite_scores.evaluate(
        ctx(
            event_type="Goal",
            home_score=1,
            away_score=0,
            minute=15,
            baseline_prob=0.51,
            is_home_favorite=True,
        ),
    )
    assert s is None
