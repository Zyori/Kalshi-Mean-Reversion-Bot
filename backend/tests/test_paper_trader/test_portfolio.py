from src.paper_trader.portfolio import Portfolio


class TestPortfolio:
    def test_initial_state(self):
        p = Portfolio(initial_bankroll_cents=50000, max_positions=15)
        assert p.bankroll_cents == 50000
        assert p.open_count == 0
        assert p.pending_wagers_cents == 0
        assert p.available_cents == 50000
        assert p.can_open()

    def test_open_position(self):
        p = Portfolio(initial_bankroll_cents=50000)
        p.open_position(1, 1000)
        assert p.open_count == 1
        assert p.pending_wagers_cents == 1000
        assert p.available_cents == 49000

    def test_close_position_win(self):
        p = Portfolio(initial_bankroll_cents=50000)
        p.open_position(1, 1000)
        p.close_position(1, 500)
        assert p.open_count == 0
        assert p.bankroll_cents == 50500

    def test_close_position_loss(self):
        p = Portfolio(initial_bankroll_cents=50000)
        p.open_position(1, 1000)
        p.close_position(1, -1000)
        assert p.bankroll_cents == 49000

    def test_max_positions_enforced(self):
        p = Portfolio(initial_bankroll_cents=100000, max_positions=2)
        p.open_position(1, 100)
        p.open_position(2, 100)
        assert not p.can_open()
        p.open_position(3, 100)
        assert p.open_count == 2

    def test_close_nonexistent_position(self):
        p = Portfolio(initial_bankroll_cents=50000)
        p.close_position(999, 500)
        assert p.bankroll_cents == 50000

    def test_multiple_positions(self):
        p = Portfolio(initial_bankroll_cents=50000)
        p.open_position(1, 1000)
        p.open_position(2, 2000)
        p.open_position(3, 500)
        assert p.pending_wagers_cents == 3500
        assert p.available_cents == 46500
        assert p.open_count == 3
