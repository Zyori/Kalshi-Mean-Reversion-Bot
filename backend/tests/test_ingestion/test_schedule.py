from src.config import settings
from src.core.types import Sport
from src.ingestion.espn_scoreboard import EspnScoreboardPoller, is_final_status, is_live_status


def test_scoreboard_interval_prefers_live_games():
    poller = EspnScoreboardPoller(queue=None, sports=[Sport.NHL])  # type: ignore[arg-type]
    poller._last_state = "live"
    assert poller.next_interval() == settings.scoreboard_live_poll_interval_s


def test_scoreboard_interval_prefers_pregame_when_no_live_games():
    poller = EspnScoreboardPoller(queue=None, sports=[Sport.NHL])  # type: ignore[arg-type]
    poller._last_state = "pregame"
    assert poller.next_interval() == settings.scoreboard_pregame_poll_interval_s


def test_scoreboard_interval_uses_idle_backoff_by_default():
    poller = EspnScoreboardPoller(queue=None, sports=[Sport.NHL])  # type: ignore[arg-type]
    poller._last_state = "idle"
    assert poller.next_interval() == settings.scoreboard_idle_poll_interval_s


def test_live_status_detection_accepts_espn_period_states():
    assert is_live_status("STATUS_FIRST_HALF") is True
    assert is_live_status("STATUS_HALFTIME") is True
    assert is_live_status("STATUS_IN_PROGRESS") is True


def test_final_status_detection_accepts_espn_terminal_states():
    assert is_final_status("STATUS_FINAL") is True
    assert is_final_status("POST") is True
    assert is_final_status("STATUS_SCHEDULED") is False
