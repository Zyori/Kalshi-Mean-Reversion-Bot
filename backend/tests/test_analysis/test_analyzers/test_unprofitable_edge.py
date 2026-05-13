from src.analysis.analyzers import unprofitable_edge

from .conftest import ctx, trade


def test_silent_below_min_trades():
    trades = [
        trade(id=i, signal_kind="e", won=False, pnl_cents=-100, stake_cents=100)
        for i in range(20)
    ]
    assert unprofitable_edge.evaluate(ctx(*trades)) == []


def test_silent_when_break_even_or_better():
    trades = [
        trade(id=i, signal_kind="e", won=True, pnl_cents=100, stake_cents=100)
        for i in range(25)
    ]
    assert unprofitable_edge.evaluate(ctx(*trades)) == []


def test_silent_when_loss_below_2x_avg_stake():
    # 25 trades with avg stake $1, total loss only $1 — below the 2× floor.
    trades = [
        trade(
            id=i,
            signal_kind="e",
            won=i % 2 == 0,
            pnl_cents=100 if i % 2 == 0 else -108,
            stake_cents=100,
        )
        for i in range(25)
    ]
    assert unprofitable_edge.evaluate(ctx(*trades)) == []


def test_flags_unprofitable_edge():
    # 25 trades, total loss > 2× avg stake.
    trades = [
        trade(id=i, signal_kind="e", won=False, pnl_cents=-100, stake_cents=100)
        for i in range(25)
    ]
    findings = unprofitable_edge.evaluate(ctx(*trades))
    assert len(findings) == 1
    assert findings[0].type == "edge_unprofitable"
    assert "retiring" in (findings[0].recommendation or "")
