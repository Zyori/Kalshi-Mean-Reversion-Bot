"""Analyzer: per-league PnL skew.

Question: are some leagues printing while others bleed? Two leagues with
very different win rates inside the same sport tell us either the edge
behaves differently per league (real signal — narrow), or one league's
markets are mis-calibrated (also useful info).

Threshold: only flag when we have ≥15 trades in a league and it's
materially different from the sport-wide rate (≥15-pt swing).
"""

from __future__ import annotations

from src.analysis.analyzers.context import AnalysisContext, Finding

MIN_LEAGUE_TRADES = 15
SKEW_THRESHOLD = 0.15


def evaluate(ctx: AnalysisContext) -> list[Finding]:
    if len(ctx.trades) < MIN_LEAGUE_TRADES:
        return []
    sport_wr = sum(1 for t in ctx.trades if t.won) / len(ctx.trades)
    findings: list[Finding] = []
    for league, trades in ctx.by_league().items():
        if league is None or len(trades) < MIN_LEAGUE_TRADES:
            continue
        wins = sum(1 for t in trades if t.won)
        league_wr = wins / len(trades)
        delta = league_wr - sport_wr
        if abs(delta) < SKEW_THRESHOLD:
            continue
        total_pnl = sum(t.pnl_cents for t in trades)
        direction = "outperforms" if delta > 0 else "underperforms"
        findings.append(
            Finding(
                type="league_skew",
                title=f"{league} {direction} the sport average",
                body=(
                    f"{len(trades)} trades in {league}: {league_wr:.0%} win rate "
                    f"vs {sport_wr:.0%} sport-wide ({delta:+.0%}). "
                    f"League PnL ${total_pnl / 100:+.2f}."
                ),
                recommendation=(
                    "Consider whether this league's market structure favors our "
                    "edges (or doesn't). Could justify narrower league focus."
                ),
                confidence=round(min(abs(delta) / 0.25, 1.0), 2),
                data={
                    "league": league,
                    "n": len(trades),
                    "league_win_rate": round(league_wr, 4),
                    "sport_win_rate": round(sport_wr, 4),
                    "delta": round(delta, 4),
                    "league_pnl_cents": total_pnl,
                },
            )
        )
    return findings
