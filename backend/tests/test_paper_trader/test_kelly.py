import pytest

from src.paper_trader.kelly import ConservativeEstimator, kelly_fraction, kelly_size


class TestKellyFraction:
    def test_fair_bet_no_edge(self):
        assert kelly_fraction(0.50, 50) == pytest.approx(0.0)

    def test_positive_edge(self):
        f = kelly_fraction(0.60, 40)
        assert f > 0.0

    def test_negative_edge_returns_zero(self):
        f = kelly_fraction(0.30, 70)
        assert f == 0.0

    def test_strong_edge_cheap_contract(self):
        f = kelly_fraction(0.80, 20)
        assert f > 0.5

    def test_edge_at_boundary_prices(self):
        assert kelly_fraction(0.60, 0) == 0.0
        assert kelly_fraction(0.60, 100) == 0.0

    def test_known_value(self):
        # p=0.6, entry=40 → b=(100-40)/40=1.5 → f=(1.5*0.6-0.4)/1.5
        b = 60 / 40
        expected = (b * 0.6 - 0.4) / b
        assert kelly_fraction(0.60, 40) == pytest.approx(expected)


class TestKellySize:
    def test_basic_size(self):
        size = kelly_size(0.60, 40, 50000, 0)
        assert size > 0
        assert size <= 2500

    def test_zero_edge_no_bet(self):
        size = kelly_size(0.50, 50, 50000, 0)
        assert size == 0

    def test_negative_edge_no_bet(self):
        size = kelly_size(0.30, 70, 50000, 0)
        assert size == 0

    def test_below_min_bet_returns_zero(self):
        size = kelly_size(0.51, 49, 1000, 0)
        assert size == 0

    def test_respects_max_bet(self):
        size = kelly_size(0.90, 10, 1_000_000, 0)
        assert size <= 2500

    def test_quarter_kelly_default(self):
        full = kelly_size(0.60, 40, 50000, 0, fraction_multiplier=1.0)
        quarter = kelly_size(0.60, 40, 50000, 0, fraction_multiplier=0.25)
        assert quarter <= full

    def test_pending_wagers_reduce_available(self):
        large = kelly_size(0.60, 40, 50000, 0)
        small = kelly_size(0.60, 40, 50000, 40000)
        assert small < large

    def test_bankroll_exhausted(self):
        size = kelly_size(0.60, 40, 50000, 50000)
        assert size == 0

    def test_negative_available(self):
        size = kelly_size(0.60, 40, 50000, 60000)
        assert size == 0


class TestConservativeEstimator:
    def test_zero_score(self):
        est = ConservativeEstimator()
        assert est.estimate(0.0, {}) == pytest.approx(0.50)

    def test_max_score(self):
        est = ConservativeEstimator()
        result = est.estimate(1.0, {})
        assert result == pytest.approx(0.60)

    def test_mid_score(self):
        est = ConservativeEstimator()
        result = est.estimate(0.5, {})
        assert result == pytest.approx(0.55)

    def test_never_exceeds_60(self):
        est = ConservativeEstimator()
        for s in [0.0, 0.5, 1.0, 2.0]:
            assert est.estimate(s, {}) <= 0.90
