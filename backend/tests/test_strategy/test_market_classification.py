from src.strategy.classifier import EventClassifier


def test_spread_market_can_flag_reversion_candidate() -> None:
    clf = EventClassifier()
    result = clf.classify(
        sport="nba",
        event_type="Turnover",
        description="Fast-break turnover after an 8-0 run",
        home_score=30,
        away_score=33,
        period="2",
        baseline_prob=0.5,
        is_home_favorite=True,
        market_category="spread",
        opening_spread_home=-4.5,
    )
    assert result == "reversion_candidate"


def test_total_market_can_flag_reversion_candidate() -> None:
    clf = EventClassifier()
    result = clf.classify(
        sport="nba",
        event_type="Timeout",
        description="Timeout after back-to-back threes",
        home_score=31,
        away_score=28,
        period="1",
        baseline_prob=0.5,
        is_home_favorite=True,
        market_category="total",
        opening_total=221.5,
    )
    assert result == "reversion_candidate"


def test_spread_large_late_move_becomes_structural_shift() -> None:
    clf = EventClassifier()
    result = clf.classify(
        sport="nfl",
        event_type="Touchdown",
        description="Late touchdown extends the lead",
        home_score=10,
        away_score=31,
        period="4",
        baseline_prob=0.5,
        is_home_favorite=True,
        market_category="spread",
        opening_spread_home=-3.5,
    )
    assert result == "structural_shift"


def test_team_total_market_can_flag_reversion_candidate() -> None:
    clf = EventClassifier()
    result = clf.classify(
        sport="mlb",
        event_type="Walk",
        description="Bases-loaded walk keeps the inning alive",
        home_score=2,
        away_score=1,
        period="5",
        baseline_prob=0.5,
        is_home_favorite=True,
        market_category="team_total",
        opening_team_total=4.5,
        team_total_side="home",
    )
    assert result == "reversion_candidate"


def test_total_without_opening_total_stays_neutral() -> None:
    clf = EventClassifier()
    result = clf.classify(
        sport="mlb",
        event_type="Home Run",
        description="Solo home run in the second inning",
        home_score=2,
        away_score=1,
        period="2",
        baseline_prob=0.5,
        is_home_favorite=True,
        market_category="total",
        opening_total=None,
    )
    assert result == "neutral"


def test_team_total_without_line_stays_neutral() -> None:
    clf = EventClassifier()
    result = clf.classify(
        sport="nba",
        event_type="Timeout",
        description="Timeout after a quick run",
        home_score=22,
        away_score=19,
        period="1",
        baseline_prob=0.5,
        is_home_favorite=True,
        market_category="team_total",
        opening_team_total=None,
        team_total_side="home",
    )
    assert result == "neutral"
