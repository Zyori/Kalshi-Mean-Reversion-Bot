import pytest

from src.analysis.accumulators import Accumulators, BucketStats, TradeRecord


def _trade(sport="nhl", event_type="pp_goal", won=True, pnl=200, conf=0.7):
    return TradeRecord(
        sport=sport,
        event_type=event_type,
        won=won,
        pnl_cents=pnl,
        confidence_score=conf,
    )


class TestBucketStats:
    def test_empty(self):
        b = BucketStats()
        assert b.count == 0
        assert b.wins == 0
        assert b.win_rate == 0.0
        assert b.total_pnl == 0
        assert b.mean_pnl == 0.0

    def test_add_and_stats(self):
        b = BucketStats()
        b.add(_trade(won=True, pnl=200))
        b.add(_trade(won=False, pnl=-100))
        b.add(_trade(won=True, pnl=150))
        assert b.count == 3
        assert b.wins == 2
        assert b.win_rate == pytest.approx(2 / 3)
        assert b.total_pnl == 250
        assert b.mean_pnl == pytest.approx(250 / 3)

    def test_rolling_window_bounded(self):
        b = BucketStats()
        for i in range(120):
            b.add(_trade(pnl=i))
        assert b.count == 100
        assert b.trades[0].pnl_cents == 20

    def test_pnl_values(self):
        b = BucketStats()
        b.add(_trade(pnl=100))
        b.add(_trade(pnl=-50))
        assert b.pnl_values == [100, -50]


class TestAccumulators:
    def test_update_populates_all_buckets(self):
        acc = Accumulators()
        acc.update(_trade(sport="nhl", event_type="pp_goal"))
        assert acc._overall.count == 1
        assert acc.get_sport_stats("nhl").count == 1
        assert acc.get_event_type_stats("pp_goal").count == 1

    def test_multiple_sports(self):
        acc = Accumulators()
        acc.update(_trade(sport="nhl"))
        acc.update(_trade(sport="nhl"))
        acc.update(_trade(sport="nba"))
        assert acc.get_sport_stats("nhl").count == 2
        assert acc.get_sport_stats("nba").count == 1
        assert acc._overall.count == 3

    def test_summary(self):
        acc = Accumulators()
        acc.update(_trade(sport="nhl", won=True, pnl=200))
        acc.update(_trade(sport="nhl", won=False, pnl=-100))
        s = acc.summary()
        assert s["overall"]["count"] == 2
        assert s["overall"]["wins"] == 1
        assert s["by_sport"]["nhl"]["count"] == 2

    @pytest.mark.asyncio
    async def test_update_async(self):
        acc = Accumulators()
        await acc.update_async(_trade())
        assert acc._overall.count == 1
