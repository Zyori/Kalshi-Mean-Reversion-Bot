from src.strategy.sports.soccer.edges import penalty_awarded

from .conftest import ctx


def test_fires_when_penalty_is_awarded():
    s = penalty_awarded.evaluate(
        ctx(event_type="Penalty", description="Penalty awarded", minute=55),
    )
    assert s is not None
    assert s.signal_kind == "penalty_awarded"


def test_silent_when_penalty_missed():
    s = penalty_awarded.evaluate(
        ctx(event_type="Penalty", description="Penalty missed by striker", minute=55),
    )
    assert s is None


def test_silent_when_penalty_saved():
    s = penalty_awarded.evaluate(
        ctx(event_type="Penalty", description="Penalty saved by goalkeeper", minute=55),
    )
    assert s is None


def test_silent_on_non_penalty_event():
    s = penalty_awarded.evaluate(
        ctx(event_type="Goal", description="Header to the bottom corner", minute=55),
    )
    assert s is None
