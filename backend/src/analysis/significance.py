import asyncio

import numpy as np
from scipy import stats

from src.analysis.accumulators import BucketStats
from src.core.logging import get_logger

logger = get_logger(__name__)

MIN_SAMPLE_SIZE = 30
ALPHA = 0.05
REGIME_CHANGE_DELTA = 0.15
REGIME_CHANGE_MIN_N = 20
RECENCY_WINDOW = 100


def test_win_rate(bucket: BucketStats) -> dict | None:
    if bucket.count < MIN_SAMPLE_SIZE:
        return None

    result = stats.binomtest(bucket.wins, bucket.count, 0.5, alternative="greater")
    return {
        "test": "binomial",
        "win_rate": round(bucket.win_rate, 4),
        "n": bucket.count,
        "p_value": round(result.pvalue, 6),
        "significant": result.pvalue < ALPHA,
    }


def test_mean_pnl(bucket: BucketStats) -> dict | None:
    if bucket.count < MIN_SAMPLE_SIZE:
        return None

    pnl = np.array(bucket.pnl_values, dtype=np.float64)
    result = stats.ttest_1samp(pnl, 0.0)
    mean = float(np.mean(pnl))
    p_one_sided = result.pvalue / 2 if mean > 0 else 1.0

    return {
        "test": "t_test",
        "mean_pnl_cents": round(mean, 2),
        "std_pnl_cents": round(float(np.std(pnl, ddof=1)), 2),
        "n": bucket.count,
        "t_stat": round(float(result.statistic), 4),
        "p_value": round(p_one_sided, 6),
        "significant": p_one_sided < ALPHA and mean > 0,
    }


def check_edge_validated(bucket: BucketStats) -> dict | None:
    wr = test_win_rate(bucket)
    pnl = test_mean_pnl(bucket)

    if not wr or not pnl:
        return None

    if wr["significant"] and pnl["significant"] and bucket.count >= MIN_SAMPLE_SIZE:
        return {
            "type": "edge_validated",
            "title": f"Edge validated: {bucket.count} trades, {wr['win_rate']:.0%} win rate",
            "body": (
                f"Win rate: {wr['win_rate']:.1%} (p={wr['p_value']:.4f}), "
                f"Mean PnL: ${pnl['mean_pnl_cents'] / 100:.2f}/trade (p={pnl['p_value']:.4f})"
            ),
            "data": {"win_rate_test": wr, "pnl_test": pnl},
            "confidence": 1 - max(wr["p_value"], pnl["p_value"]),
        }
    return None


def check_regime_change(all_time: BucketStats, recent_n: int = 30) -> dict | None:
    if all_time.count < REGIME_CHANGE_MIN_N + recent_n:
        return None

    recent_trades = all_time.trades[-recent_n:]
    recent_wins = sum(1 for t in recent_trades if t.won)
    recent_wr = recent_wins / len(recent_trades)
    all_wr = all_time.win_rate
    delta = recent_wr - all_wr

    if abs(delta) > REGIME_CHANGE_DELTA and len(recent_trades) >= REGIME_CHANGE_MIN_N:
        insight_type = "edge_degraded" if delta < 0 else "edge_validated"
        return {
            "type": insight_type,
            "title": f"Regime change: {delta:+.0%} win rate shift",
            "body": (
                f"Recent {recent_n} trades: {recent_wr:.1%} vs all-time {all_wr:.1%} "
                f"(delta: {delta:+.1%})"
            ),
            "data": {
                "recent_win_rate": round(recent_wr, 4),
                "all_time_win_rate": round(all_wr, 4),
                "delta": round(delta, 4),
                "recent_n": recent_n,
            },
            "confidence": min(abs(delta) / 0.30, 1.0),
        }
    return None


async def run_significance_checks(bucket: BucketStats, label: str) -> list[dict]:
    def _check():
        insights = []
        edge = check_edge_validated(bucket)
        if edge:
            edge["label"] = label
            insights.append(edge)
        regime = check_regime_change(bucket)
        if regime:
            regime["label"] = label
            insights.append(regime)
        return insights

    return await asyncio.to_thread(_check)
