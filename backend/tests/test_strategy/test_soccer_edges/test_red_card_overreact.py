from src.strategy.sports.soccer.edges import red_card_overreact

from .conftest import ctx


def test_fires_on_red_card_event():
    s = red_card_overreact.evaluate(
        ctx(event_type="Red Card", description="Straight red", minute=40),
    )
    assert s is not None
    assert s.signal_kind == "red_card_overreact"


def test_fires_when_description_says_sent_off_even_without_red_card_type():
    s = red_card_overreact.evaluate(
        ctx(event_type="Foul", description="Player sent off after VAR review", minute=42),
    )
    assert s is not None


def test_silent_on_non_red_card_event():
    s = red_card_overreact.evaluate(
        ctx(event_type="Goal", description="Header", minute=40),
    )
    assert s is None


def test_silent_very_late_in_match():
    s = red_card_overreact.evaluate(
        ctx(event_type="Red Card", description="Straight red", minute=82),
    )
    assert s is None
