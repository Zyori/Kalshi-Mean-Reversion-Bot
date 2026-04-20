import pytest

from src.strategy.scorer import normalize, score_opportunity


class TestNormalize:
    def test_mid_range(self):
        assert normalize(0.50, 0.0, 1.0) == pytest.approx(0.50)

    def test_at_min(self):
        assert normalize(0.05, 0.05, 0.30) == pytest.approx(0.0)

    def test_at_max(self):
        assert normalize(0.30, 0.05, 0.30) == pytest.approx(1.0)

    def test_below_min_clamped(self):
        assert normalize(0.01, 0.05, 0.30) == pytest.approx(0.0)

    def test_above_max_clamped(self):
        assert normalize(0.50, 0.05, 0.30) == pytest.approx(1.0)

    def test_degenerate_range(self):
        assert normalize(0.5, 0.5, 0.5) == pytest.approx(0.0)


class TestScoreOpportunity:
    def test_max_inputs(self):
        result = score_opportunity(0.30, 0.90)
        assert result == pytest.approx(1.0, abs=0.001)

    def test_min_inputs(self):
        result = score_opportunity(0.05, 0.25)
        assert result == pytest.approx(0.0, abs=0.001)

    def test_midpoint(self):
        result = score_opportunity(0.175, 0.575)
        assert 0.4 <= result <= 0.6

    def test_high_deviation_low_time(self):
        result = score_opportunity(0.30, 0.25)
        assert result == pytest.approx(0.6, abs=0.001)

    def test_low_deviation_high_time(self):
        result = score_opportunity(0.05, 0.90)
        assert result == pytest.approx(0.4, abs=0.001)

    def test_returns_bounded(self):
        for dev in [0.0, 0.05, 0.15, 0.30, 0.50]:
            for time in [0.0, 0.25, 0.50, 0.90, 1.0]:
                result = score_opportunity(dev, time)
                assert 0.0 <= result <= 1.0
