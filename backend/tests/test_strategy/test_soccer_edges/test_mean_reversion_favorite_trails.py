from src.strategy.sports.soccer.edges import mean_reversion_favorite_trails

from .conftest import ctx


def test_fires_when_favorite_trails_after_goal_early():
    # Home favorite (baseline 0.6) is down 0-1 after an early underdog goal.
    s = mean_reversion_favorite_trails.evaluate(
        ctx(
            event_type="Goal",
            home_score=0,
            away_score=1,
            minute=20,
            baseline_prob=0.6,
            is_home_favorite=True,
        ),
    )
    assert s is not None
    assert s.signal_kind == "mean_reversion_favorite_trails"
    assert s.classification == "reversion_candidate"


def test_silent_when_favorite_is_not_behind():
    s = mean_reversion_favorite_trails.evaluate(
        ctx(
            event_type="Goal",
            home_score=1,
            away_score=0,
            minute=20,
            baseline_prob=0.6,
            is_home_favorite=True,
        ),
    )
    assert s is None


def test_fires_with_unknown_baseline_for_research_volume():
    # Research-mode: when there's no clear favorite (baseline ~ 0.5,
    # typical when Odds API has no line and Kalshi-fallback missed),
    # the edge still fires so we collect outcomes. Analysis later can
    # filter by whether a clear baseline existed.
    s = mean_reversion_favorite_trails.evaluate(
        ctx(
            event_type="Goal",
            home_score=0,
            away_score=1,
            minute=20,
            baseline_prob=0.50,
            is_home_favorite=True,
        ),
    )
    assert s is not None
    assert s.signal_kind == "mean_reversion_favorite_trails"


def test_silent_when_event_is_not_a_goal():
    s = mean_reversion_favorite_trails.evaluate(
        ctx(
            event_type="Yellow Card",
            home_score=0,
            away_score=1,
            minute=20,
            baseline_prob=0.6,
            is_home_favorite=True,
        ),
    )
    assert s is None


def test_silent_late_in_match():
    s = mean_reversion_favorite_trails.evaluate(
        ctx(
            event_type="Goal",
            home_score=0,
            away_score=1,
            minute=78,
            baseline_prob=0.6,
            is_home_favorite=True,
        ),
    )
    assert s is None


def test_silent_when_deficit_too_large():
    s = mean_reversion_favorite_trails.evaluate(
        ctx(
            event_type="Goal",
            home_score=0,
            away_score=3,
            minute=40,
            baseline_prob=0.6,
            is_home_favorite=True,
        ),
    )
    assert s is None
