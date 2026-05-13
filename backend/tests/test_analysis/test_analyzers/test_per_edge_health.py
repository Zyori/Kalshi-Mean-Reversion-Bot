from src.analysis.analyzers import per_edge_health

from .conftest import ctx, trade


def _edges_with_n_each(*, edge: str, wins: int, losses: int):
    return [
        *(trade(id=i, signal_kind=edge, won=True, pnl_cents=100) for i in range(wins)),
        *(
            trade(id=1000 + i, signal_kind=edge, won=False, pnl_cents=-100)
            for i in range(losses)
        ),
    ]


def test_silent_when_sample_too_small_for_any_callout():
    # 4 trades: below MIN_TRADES_FOR_CALLOUT (5); no Finding at all.
    findings = per_edge_health.evaluate(
        ctx(*_edges_with_n_each(edge="goal", wins=2, losses=2))
    )
    assert findings == []


def test_emits_watching_finding_when_sample_under_verdict_threshold():
    # 10 trades: between callout (5) and verdict (15) — observation only.
    findings = per_edge_health.evaluate(
        ctx(*_edges_with_n_each(edge="goal", wins=5, losses=5))
    )
    assert len(findings) == 1
    assert findings[0].type == "edge_observation"
    assert "Watching" in findings[0].title
    assert "too small" in (findings[0].recommendation or "")


def test_flags_unprofitable_edge_when_ci_caps_below_break_even():
    # 30 trades, 6 wins → 20% win rate; CI high should sit well under 50%.
    findings = per_edge_health.evaluate(
        ctx(*_edges_with_n_each(edge="mean_rev", wins=6, losses=24))
    )
    assert len(findings) == 1
    assert findings[0].type == "edge_degraded"


def test_flags_validated_edge_when_ci_floor_above_break_even():
    # 40 trades, 30 wins → 75% win rate; CI low ≈ 0.60, comfortably > 0.55.
    findings = per_edge_health.evaluate(
        ctx(*_edges_with_n_each(edge="trend_affirm", wins=30, losses=10))
    )
    assert len(findings) == 1
    assert findings[0].type == "edge_validated"


def test_emits_mixed_signal_when_ci_straddles_breakeven():
    # 20 trades, 10 wins → exactly 50%; CI will straddle.
    findings = per_edge_health.evaluate(
        ctx(*_edges_with_n_each(edge="coinflip", wins=10, losses=10))
    )
    assert len(findings) == 1
    assert findings[0].type == "edge_observation"
    assert "Mixed signal" in findings[0].title


def test_ignores_trades_with_no_signal_kind():
    # Untagged trades (signal_kind=None) shouldn't synthesize a "None" edge.
    findings = per_edge_health.evaluate(
        ctx(*[trade(id=i, signal_kind=None) for i in range(20)])
    )
    assert findings == []
