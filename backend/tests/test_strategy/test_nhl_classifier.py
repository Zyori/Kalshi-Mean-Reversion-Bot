import pytest

from src.strategy.sports.nhl import NhlClassifier


@pytest.fixture
def clf():
    return NhlClassifier()


class TestNhlClassifierReversionCandidates:
    def test_pp_goal_against_favorite_period1(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="Power Play Goal",
            description="Power play goal scored",
            home_score=0,
            away_score=1,
            period="1",
            baseline_prob=0.65,
            is_home_favorite=True,
        )
        assert result == "reversion_candidate"

    def test_pp_goal_against_favorite_period2(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="goal",
            description="Power play goal by opponent",
            home_score=1,
            away_score=2,
            period="2",
            baseline_prob=0.62,
            is_home_favorite=True,
        )
        assert result == "reversion_candidate"

    def test_es_goal_against_favorite_period1(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="Goal",
            description="Even strength goal",
            home_score=0,
            away_score=1,
            period="1",
            baseline_prob=0.70,
            is_home_favorite=True,
        )
        assert result == "reversion_candidate"

    def test_away_favorite_behind(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="Power Play Goal",
            description="Power play goal",
            home_score=2,
            away_score=1,
            period="1",
            baseline_prob=0.65,
            is_home_favorite=False,
        )
        assert result == "reversion_candidate"


class TestNhlClassifierStructuralShift:
    def test_goalie_pulled(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="event",
            description="Goalie pulled for extra attacker",
            home_score=2,
            away_score=4,
            period="3",
            baseline_prob=0.55,
            is_home_favorite=True,
        )
        assert result == "structural_shift"

    def test_empty_net(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="event",
            description="Empty net goalie situation",
            home_score=3,
            away_score=5,
            period="3",
            baseline_prob=0.60,
            is_home_favorite=True,
        )
        assert result == "structural_shift"

    def test_large_deficit_period3(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="Goal",
            description="Goal scored",
            home_score=0,
            away_score=4,
            period="3",
            baseline_prob=0.70,
            is_home_favorite=True,
        )
        assert result == "structural_shift"

    def test_large_deficit_period2(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="Goal",
            description="Goal scored",
            home_score=0,
            away_score=4,
            period="2",
            baseline_prob=0.70,
            is_home_favorite=True,
        )
        assert result == "structural_shift"


class TestNhlClassifierNeutral:
    def test_favorite_not_behind(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="Power Play Goal",
            description="Power play goal",
            home_score=2,
            away_score=1,
            period="1",
            baseline_prob=0.70,
            is_home_favorite=True,
        )
        assert result == "neutral"

    def test_low_baseline_pp(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="Power Play Goal",
            description="Power play goal",
            home_score=0,
            away_score=1,
            period="1",
            baseline_prob=0.55,
            is_home_favorite=True,
        )
        assert result == "neutral"

    def test_es_goal_period2_not_candidate(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="Goal",
            description="Even strength goal",
            home_score=1,
            away_score=2,
            period="2",
            baseline_prob=0.70,
            is_home_favorite=True,
        )
        assert result == "neutral"

    def test_tied_game(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="Goal",
            description="Goal scored",
            home_score=2,
            away_score=2,
            period="2",
            baseline_prob=0.65,
            is_home_favorite=True,
        )
        assert result == "neutral"

    def test_invalid_period(self, clf: NhlClassifier):
        result = clf.classify_event(
            event_type="Goal",
            description="Goal scored",
            home_score=0,
            away_score=1,
            period="OT",
            baseline_prob=0.70,
            is_home_favorite=True,
        )
        assert result == "neutral"


class TestNhlClassifierCustomParams:
    def test_stricter_pp_threshold(self):
        clf = NhlClassifier({"min_favorite_prob_pp": 0.70})
        result = clf.classify_event(
            event_type="Power Play Goal",
            description="Power play goal",
            home_score=0,
            away_score=1,
            period="2",
            baseline_prob=0.65,
            is_home_favorite=True,
        )
        assert result == "neutral"

    def test_higher_deficit_tolerance(self):
        clf = NhlClassifier({"max_deficit_reversion": 4})
        result = clf.classify_event(
            event_type="Goal",
            description="Goal scored",
            home_score=0,
            away_score=4,
            period="2",
            baseline_prob=0.70,
            is_home_favorite=True,
        )
        assert result == "neutral"
