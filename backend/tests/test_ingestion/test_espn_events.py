from src.core.types import Sport
from src.ingestion.espn_events import _is_significant_event, _normalize_event_type


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


def test_nba_running_shot_is_not_significant_just_because_of_running():
    assert not _is_significant_event(
        "Running Layup Shot",
        "Tyrese Maxey makes running layup",
        Sport.NBA,
    )


def test_nba_scoring_run_is_significant():
    assert _is_significant_event(
        "Stoppage",
        "Celtics on a 12-2 run forcing a timeout",
        Sport.NBA,
    )


def test_normalize_nba_shot_event_types():
    assert (
        _normalize_event_type(
            "Running Layup Shot",
            "Tyrese Maxey makes running layup",
            Sport.NBA,
        )
        == "Score"
    )
    assert (
        _normalize_event_type(
            "Running Jump Shot",
            "Sam Hauser misses 23-foot running jump shot",
            Sport.NBA,
        )
        == "Missed Shot"
    )


def test_normalize_nhl_minor_to_penalty():
    assert (
        _normalize_event_type(
            "Penalty Shot Infraction",
            "Yanni Gourde Minor against Arber Xhekaj",
            Sport.NHL,
        )
        == "Penalty"
    )
