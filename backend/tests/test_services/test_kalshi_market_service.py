from datetime import UTC, datetime

from src.models.game import Game
from src.services.kalshi_market_service import (
    _best_bid,
    _depth,
    _title_matches_game,
    _within_match_window,
    _yes_side_matches_home,
)


def _game(**overrides) -> Game:
    payload = {
        "id": 1,
        "sport": "nba",
        "home_team": "Los Angeles Lakers",
        "away_team": "Golden State Warriors",
        "start_time": datetime(2026, 4, 21, 2, 0, tzinfo=UTC),
        "status": "scheduled",
    }
    payload.update(overrides)
    return Game(**payload)


def test_title_matches_full_game_name() -> None:
    game = _game()
    market_row = {"event_title": "Warriors vs Lakers Winner?"}
    assert _title_matches_game(game, market_row) is True


def test_yes_side_matches_home_team_alias() -> None:
    game = _game(home_team="New York Knicks")
    market_row = {"yes_sub_title": "New York"}
    assert _yes_side_matches_home(game, market_row) is True


def test_within_match_window_accepts_same_day_market() -> None:
    game = _game()
    market_row = {"expected_expiration_time": "2026-04-21T03:30:00Z"}
    assert _within_match_window(game, market_row) is True


def test_within_match_window_rejects_distant_market() -> None:
    game = _game()
    market_row = {"expected_expiration_time": "2026-04-24T03:30:00Z"}
    assert _within_match_window(game, market_row) is False


def test_best_bid_and_depth_from_orderbook_levels() -> None:
    levels = [["0.2700", "159.00"], ["0.3100", "80.00"]]
    assert _best_bid(levels) == 31
    assert _depth(levels) == 239
