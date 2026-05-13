"""Ordered registry of analyzers. Each pass walks them in order and
persists any Findings they emit. Adding a new analyzer is: write a
file in this directory, append its module here.
"""

from collections.abc import Callable

from src.analysis.analyzers import (
    edge_decay,
    league_skew,
    per_edge_health,
    unprofitable_edge,
)
from src.analysis.analyzers.context import AnalysisContext, Finding

Analyzer = Callable[[AnalysisContext], list[Finding]]

ANALYZERS: tuple[Analyzer, ...] = (
    per_edge_health.evaluate,
    edge_decay.evaluate,
    unprofitable_edge.evaluate,
    league_skew.evaluate,
)


def run_all(ctx: AnalysisContext) -> list[Finding]:
    """Walk every analyzer and concatenate their findings."""
    out: list[Finding] = []
    for analyzer in ANALYZERS:
        out.extend(analyzer(ctx))
    return out
