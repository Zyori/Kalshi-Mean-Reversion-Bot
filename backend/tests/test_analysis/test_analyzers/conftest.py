"""Shared builders for analyzer tests."""

from src.analysis.analyzers.context import AnalysisContext, TradeOutcome


def trade(
    *,
    id: int = 1,
    signal_kind: str = "mean_reversion_favorite_trails",
    won: bool = True,
    pnl_cents: int = 100,
    stake_cents: int = 100,
    league: str | None = "KXLALIGAGAME",
) -> TradeOutcome:
    return TradeOutcome(
        id=id,
        sport="soccer",
        signal_kind=signal_kind,
        side="yes",
        entry_price_adj=50,
        kelly_size_cents=stake_cents,
        pnl_cents=pnl_cents,
        won=won,
        league_slug=league,
    )


def ctx(*trades) -> AnalysisContext:
    return AnalysisContext(sport="soccer", trades=list(trades))
