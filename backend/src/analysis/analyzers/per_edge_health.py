"""Analyzer: per-edge win-rate health.

Question: for each signal_kind (edge), is the win-rate confidence interval
high enough to be worth keeping, low enough to flag, or too uncertain to
tell yet?

Thresholds chosen to be appropriately humble at small N — we'd rather say
"insufficient sample" than declare an edge dead at 9 trades.
"""

from __future__ import annotations

from src.analysis.analyzers.context import AnalysisContext, Finding
from src.analysis.analyzers.stats import wilson_ci

MIN_TRADES_FOR_VERDICT = 15
MIN_TRADES_FOR_CALLOUT = 5


def evaluate(ctx: AnalysisContext) -> list[Finding]:
    findings: list[Finding] = []
    for edge, trades in ctx.by_signal_kind().items():
        if edge is None:
            continue
        n = len(trades)
        if n < MIN_TRADES_FOR_CALLOUT:
            continue
        wins = sum(1 for t in trades if t.won)
        win_rate = wins / n
        ci_low, ci_high = wilson_ci(wins, n)
        total_pnl = sum(t.pnl_cents for t in trades)
        body = (
            f"{n} resolved trades, {wins}W / {n - wins}L. "
            f"Win rate {win_rate:.0%} (95% CI {ci_low:.0%}–{ci_high:.0%}). "
            f"Total PnL ${total_pnl / 100:+.2f}."
        )

        if n < MIN_TRADES_FOR_VERDICT:
            findings.append(
                Finding(
                    type="edge_observation",
                    title=f"Watching: {edge}",
                    body=body,
                    recommendation=(
                        f"Sample is too small ({n} trades) to draw conclusions. "
                        f"Hold for more data."
                    ),
                    confidence=0.3,
                    data={
                        "edge": edge,
                        "n": n,
                        "win_rate": round(win_rate, 4),
                        "ci_low": round(ci_low, 4),
                        "ci_high": round(ci_high, 4),
                        "total_pnl_cents": total_pnl,
                    },
                )
            )
            continue

        if ci_high < 0.50:
            findings.append(
                Finding(
                    type="edge_degraded",
                    title=f"Edge underperforming: {edge}",
                    body=body,
                    recommendation=(
                        "Win rate's 95% CI tops out below break-even. "
                        "Consider tightening this edge's triggers or retiring it."
                    ),
                    confidence=round(1 - ci_high, 2),
                    data={
                        "edge": edge,
                        "n": n,
                        "win_rate": round(win_rate, 4),
                        "ci_low": round(ci_low, 4),
                        "ci_high": round(ci_high, 4),
                        "total_pnl_cents": total_pnl,
                    },
                )
            )
        elif ci_low > 0.55:
            findings.append(
                Finding(
                    type="edge_validated",
                    title=f"Edge looks real: {edge}",
                    body=body,
                    recommendation=(
                        "Win rate's 95% CI sits comfortably above break-even. "
                        "Worth considering for tightened (non-research) trading."
                    ),
                    confidence=round(ci_low, 2),
                    data={
                        "edge": edge,
                        "n": n,
                        "win_rate": round(win_rate, 4),
                        "ci_low": round(ci_low, 4),
                        "ci_high": round(ci_high, 4),
                        "total_pnl_cents": total_pnl,
                    },
                )
            )
        else:
            findings.append(
                Finding(
                    type="edge_observation",
                    title=f"Mixed signal: {edge}",
                    body=body,
                    recommendation=(
                        "Win rate's CI straddles break-even — no verdict yet. "
                        "Keep collecting."
                    ),
                    confidence=0.4,
                    data={
                        "edge": edge,
                        "n": n,
                        "win_rate": round(win_rate, 4),
                        "ci_low": round(ci_low, 4),
                        "ci_high": round(ci_high, 4),
                        "total_pnl_cents": total_pnl,
                    },
                )
            )
    return findings
