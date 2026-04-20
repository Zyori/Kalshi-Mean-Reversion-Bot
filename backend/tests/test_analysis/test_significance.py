import pytest

from src.analysis.accumulators import BucketStats, TradeRecord
from src.analysis.significance import (
    check_edge_validated,
    check_regime_change,
    run_significance_checks,
)
from src.analysis.significance import (
    test_mean_pnl as sig_test_mean_pnl,
)
from src.analysis.significance import (
    test_win_rate as sig_test_win_rate,
)


def _make_bucket(wins: int, losses: int, pnl_per_win: int = 200, pnl_per_loss: int = -100):
    b = BucketStats()
    for _ in range(wins):
        b.add(TradeRecord("nhl", "test", True, pnl_per_win, 0.7))
    for _ in range(losses):
        b.add(TradeRecord("nhl", "test", False, pnl_per_loss, 0.7))
    return b


class TestWinRateTest:
    def test_below_min_sample(self):
        bucket = _make_bucket(20, 5)
        assert sig_test_win_rate(bucket) is None

    def test_significant_win_rate(self):
        bucket = _make_bucket(25, 10)
        result = sig_test_win_rate(bucket)
        assert result is not None
        assert result["significant"]
        assert result["win_rate"] > 0.5

    def test_coin_flip_not_significant(self):
        bucket = _make_bucket(15, 15)
        result = sig_test_win_rate(bucket)
        assert result is not None
        assert not result["significant"]

    def test_losing_not_significant(self):
        bucket = _make_bucket(10, 25)
        result = sig_test_win_rate(bucket)
        assert result is not None
        assert not result["significant"]


class TestMeanPnlTest:
    def test_below_min_sample(self):
        bucket = _make_bucket(10, 5)
        assert sig_test_mean_pnl(bucket) is None

    def test_positive_mean_significant(self):
        bucket = _make_bucket(25, 10)
        result = sig_test_mean_pnl(bucket)
        assert result is not None
        assert result["mean_pnl_cents"] > 0

    def test_negative_mean_not_significant(self):
        bucket = _make_bucket(5, 30)
        result = sig_test_mean_pnl(bucket)
        assert result is not None
        assert not result["significant"]


class TestEdgeValidated:
    def test_strong_edge(self):
        bucket = _make_bucket(28, 7)
        result = check_edge_validated(bucket)
        assert result is not None
        assert result["type"] == "edge_validated"

    def test_weak_edge_not_validated(self):
        bucket = _make_bucket(17, 16)
        result = check_edge_validated(bucket)
        assert result is None

    def test_below_sample_size(self):
        bucket = _make_bucket(15, 5)
        assert check_edge_validated(bucket) is None


class TestRegimeChange:
    def test_no_change(self):
        b = BucketStats()
        for _ in range(60):
            b.add(TradeRecord("nhl", "test", True, 200, 0.7))
            b.add(TradeRecord("nhl", "test", False, -100, 0.7))
        assert check_regime_change(b) is None

    def test_degradation_detected(self):
        b = BucketStats()
        for _ in range(40):
            b.add(TradeRecord("nhl", "test", True, 200, 0.7))
        for _ in range(30):
            b.add(TradeRecord("nhl", "test", False, -100, 0.7))
        result = check_regime_change(b, recent_n=30)
        assert result is not None
        assert result["type"] == "edge_degraded"

    def test_improvement_detected(self):
        b = BucketStats()
        for _ in range(40):
            b.add(TradeRecord("nhl", "test", False, -100, 0.7))
        for _ in range(30):
            b.add(TradeRecord("nhl", "test", True, 200, 0.7))
        result = check_regime_change(b, recent_n=30)
        assert result is not None
        assert result["type"] == "edge_validated"

    def test_insufficient_data(self):
        bucket = _make_bucket(10, 10)
        assert check_regime_change(bucket) is None


class TestRunSignificanceChecks:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        bucket = _make_bucket(28, 7)
        results = await run_significance_checks(bucket, "test_label")
        assert isinstance(results, list)
        assert len(results) > 0
        assert all("label" in r for r in results)
