from src.core.types import Sport
from src.ingestion.espn_events import _is_significant_event


def test_nhl_power_play_is_significant():
    assert _is_significant_event("Penalty", "Power play coming for Edmonton", Sport.NHL)


def test_soccer_var_controversy_is_significant():
    assert _is_significant_event(
        "Review",
        "VAR review for possible penalty after controversial handball",
        Sport.SOCCER,
    )


def test_nfl_timeout_and_injury_are_significant():
    assert _is_significant_event(
        "Timeout",
        "Official timeout after injury to the quarterback",
        Sport.NFL,
    )


def test_routine_play_is_not_significant():
    assert not _is_significant_event(
        "Pass",
        "Short completion over the middle for four yards",
        Sport.NFL,
    )
