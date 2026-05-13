from src.analysis.analyzers import league_skew

from .conftest import ctx, trade


def _league(league: str, wins: int, losses: int, start_id: int = 0):
    return [
        *(
            trade(id=start_id + i, league=league, won=True, pnl_cents=100)
            for i in range(wins)
        ),
        *(
            trade(
                id=start_id + 1000 + i,
                league=league,
                won=False,
                pnl_cents=-100,
            )
            for i in range(losses)
        ),
    ]


def test_silent_when_total_dataset_too_small():
    assert league_skew.evaluate(ctx(*_league("KXEPLGAME", 5, 5))) == []


def test_flags_outperforming_league():
    # La Liga 14/15 (93%), EPL 5/15 (33%). Sport-wide 19/30 (63%).
    # La Liga delta = +30%, well past the 15% skew threshold.
    trades = [
        *_league("KXLALIGAGAME", 14, 1, start_id=0),
        *_league("KXEPLGAME", 5, 10, start_id=2000),
    ]
    findings = league_skew.evaluate(ctx(*trades))
    titles = [f.title for f in findings]
    assert any("KXLALIGAGAME outperforms" in t for t in titles)


def test_silent_when_only_one_league_present():
    # Single-league dataset: delta vs sport-average is zero by construction.
    trades = _league("KXLALIGAGAME", 10, 10)
    findings = league_skew.evaluate(ctx(*trades))
    assert findings == []
