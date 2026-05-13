from src.analysis.analyzers import edge_decay

from .conftest import ctx, trade


def _seq(edge: str, wins_pattern: list[bool]) -> list:
    return [trade(id=i, signal_kind=edge, won=w) for i, w in enumerate(wins_pattern)]


def test_silent_when_insufficient_history():
    # 30 wins + 14 recent — below 30+15 minimum total.
    pattern = [True] * 30 + [True] * 14
    assert edge_decay.evaluate(ctx(*_seq("e", pattern))) == []


def test_flags_decay_when_recent_window_drops_off():
    # 30 all-time wins, then 15 losses tacked on. All-time WR drops from 100% to
    # 30/45=67%, recent WR is 0% — delta ≈ -67%, well above threshold.
    pattern = [True] * 30 + [False] * 15
    findings = edge_decay.evaluate(ctx(*_seq("e", pattern)))
    assert len(findings) == 1
    assert findings[0].type == "regime_change"
    assert "decayed" in findings[0].title


def test_flags_improvement_when_recent_window_outperforms():
    pattern = [False] * 30 + [True] * 15
    findings = edge_decay.evaluate(ctx(*_seq("e", pattern)))
    assert len(findings) == 1
    assert "improved" in findings[0].title


def test_silent_when_delta_under_threshold():
    # Steady 50% throughout — no regime change.
    pattern = [True, False] * 25  # 50 trades, 50%
    assert edge_decay.evaluate(ctx(*_seq("e", pattern))) == []
