from src.strategy.sports.mlb import MlbClassifier
from src.strategy.sports.nba import NbaClassifier
from src.strategy.sports.nfl import NflClassifier
from src.strategy.sports.soccer import SoccerClassifier


def test_mlb_early_recoverable_deficit_is_candidate() -> None:
    clf = MlbClassifier()
    result = clf.classify_event(
        event_type="Home Run",
        description="Pitch 3 : Ball In Play",
        home_score=0,
        away_score=2,
        period="1",
        baseline_prob=0.58,
        is_home_favorite=True,
    )
    assert result == "reversion_candidate"


def test_nba_early_run_against_favorite_is_candidate() -> None:
    clf = NbaClassifier()
    result = clf.classify_event(
        event_type="Full Timeout",
        description="Celtics Full timeout",
        home_score=8,
        away_score=16,
        period="1",
        baseline_prob=0.64,
        is_home_favorite=True,
    )
    assert result == "reversion_candidate"


def test_nfl_early_one_score_deficit_is_candidate() -> None:
    clf = NflClassifier()
    result = clf.classify_event(
        event_type="Pass Touchdown",
        description="Touchdown pass to the underdog",
        home_score=0,
        away_score=7,
        period="1",
        baseline_prob=0.61,
        is_home_favorite=True,
    )
    assert result == "reversion_candidate"


def test_soccer_single_goal_early_deficit_is_candidate() -> None:
    clf = SoccerClassifier()
    result = clf.classify_event(
        event_type="Throw In",
        description="Restart after conceding",
        home_score=0,
        away_score=1,
        period="22",
        baseline_prob=0.57,
        is_home_favorite=True,
    )
    assert result == "reversion_candidate"


def test_soccer_red_card_stays_structural_shift() -> None:
    clf = SoccerClassifier()
    result = clf.classify_event(
        event_type="Red Card",
        description="Straight red to the favorite",
        home_score=0,
        away_score=0,
        period="31",
        baseline_prob=0.64,
        is_home_favorite=True,
    )
    assert result == "structural_shift"
