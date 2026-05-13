"""Analyzer: edges with a statistically-meaningful negative PnL.

Question: has any edge accumulated enough trades to confidently say it
loses money? Distinct from per_edge_health: that one looks at win rate
in isolation; this one looks at the actual dollar damage.

Threshold: ≥25 trades and total PnL more negative than 2× the average
stake — i.e. we've lost more than two bets' worth of value across the
sample. Not a formal statistical test, but a practical floor.
"""

from __future__ import annotations

from src.analysis.analyzers.context import AnalysisContext, Finding

MIN_TRADES = 25


def evaluate(ctx: AnalysisContext) -> list[Finding]:
    findings: list[Finding] = []
    for edge, trades in ctx.by_signal_kind().items():
        if edge is None or len(trades) < MIN_TRADES:
            continue
        total_pnl = sum(t.pnl_cents for t in trades)
        avg_stake = sum(t.kelly_size_cents for t in trades) / len(trades)
        if total_pnl >= 0:
            continue
        # Require the loss to be larger than ~2 average stakes — otherwise
        # we'd flag noise.
        if total_pnl > -2 * avg_stake:
            continue
        findings.append(
            Finding(
                type="edge_unprofitable",
                title=f"Edge bleeding money: {edge}",
                body=(
                    f"{len(trades)} trades, total PnL ${total_pnl / 100:+.2f}, "
                    f"average stake ${avg_stake / 100:.2f}."
                ),
                recommendation=(
                    "Cumulative loss exceeds 2× the average stake. Recommend "
                    "retiring this edge from research mode or narrowing its "
                    "trigger before more bankroll bleeds."
                ),
                confidence=round(min(abs(total_pnl) / (5 * avg_stake), 1.0), 2),
                data={
                    "edge": edge,
                    "n": len(trades),
                    "total_pnl_cents": total_pnl,
                    "avg_stake_cents": round(avg_stake),
                },
            )
        )
    return findings
