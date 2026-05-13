"""Shared inputs for analyzer functions.

Analyzers read trade outcomes already loaded into memory (rather than
hitting the DB themselves) so the per-question modules stay pure and easy
to test. The analyzer loop builds an AnalysisContext once per pass and
passes it to every analyzer in the registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TradeOutcome:
    """One resolved paper trade, denormalized for the analyzers' use."""

    id: int
    sport: str
    signal_kind: str | None
    side: str
    entry_price_adj: int
    kelly_size_cents: int
    pnl_cents: int
    won: bool
    league_slug: str | None  # e.g. KXLALIGAGAME — pulled from market ticker prefix


@dataclass
class AnalysisContext:
    """Snapshot of resolved-trade state used by every analyzer in one pass."""

    sport: str
    trades: list[TradeOutcome] = field(default_factory=list)

    def by_signal_kind(self) -> dict[str | None, list[TradeOutcome]]:
        out: dict[str | None, list[TradeOutcome]] = {}
        for t in self.trades:
            out.setdefault(t.signal_kind, []).append(t)
        return out

    def by_league(self) -> dict[str | None, list[TradeOutcome]]:
        out: dict[str | None, list[TradeOutcome]] = {}
        for t in self.trades:
            out.setdefault(t.league_slug, []).append(t)
        return out


@dataclass(frozen=True)
class Finding:
    """One conclusion an analyzer drew about the dataset.

    Lands in the `insights` table with status='pending_review'. The
    operator approves or dismisses from the dashboard."""

    type: str
    title: str
    body: str
    recommendation: str | None = None
    confidence: float | None = None
    data: dict | None = None
