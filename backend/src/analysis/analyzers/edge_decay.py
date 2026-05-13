"""Analyzer: regime change within an edge.

Question: has any edge's recent-N win rate diverged meaningfully from its
all-time win rate? If yes, something about the market or the strategy
shifted and we want to know.

Conservative: needs ≥30 all-time and ≥15 in the recent window before we
even compare, then a ≥15-percentage-point swing to call it.
"""

from __future__ import annotations

from src.analysis.analyzers.context import AnalysisContext, Finding

ALL_TIME_MIN = 30
RECENT_WINDOW = 15
SHIFT_THRESHOLD = 0.15


def evaluate(ctx: AnalysisContext) -> list[Finding]:
    findings: list[Finding] = []
    for edge, trades in ctx.by_signal_kind().items():
        if edge is None or len(trades) < ALL_TIME_MIN + RECENT_WINDOW:
            continue
        all_wr = sum(1 for t in trades if t.won) / len(trades)
        recent = trades[-RECENT_WINDOW:]
        recent_wr = sum(1 for t in recent if t.won) / len(recent)
        delta = recent_wr - all_wr
        if abs(delta) < SHIFT_THRESHOLD:
            continue
        direction = "improved" if delta > 0 else "decayed"
        findings.append(
            Finding(
                type="regime_change",
                title=f"Edge {direction}: {edge}",
                body=(
                    f"Last {RECENT_WINDOW} trades won {recent_wr:.0%} vs all-time "
                    f"{all_wr:.0%} ({delta:+.0%} shift)."
                ),
                recommendation=(
                    "Recent regime differs from baseline — investigate whether "
                    "the underlying signal still holds, or whether opponents "
                    "have adapted."
                ),
                confidence=round(min(abs(delta) / 0.30, 1.0), 2),
                data={
                    "edge": edge,
                    "all_time_n": len(trades),
                    "all_time_win_rate": round(all_wr, 4),
                    "recent_n": len(recent),
                    "recent_win_rate": round(recent_wr, 4),
                    "delta": round(delta, 4),
                },
            )
        )
    return findings
