import pytest

from src.paper_trader.portfolio import Portfolio
from src.paper_trader.simulator import PaperTradeSimulator, calculate_slippage


class TestCalculateSlippage:
    def test_minimum_slippage(self):
        assert calculate_slippage(50) >= 1

    def test_half_percent_base(self):
        assert calculate_slippage(80) == 1  # 80 * 0.005 = 0.4, max(1, 0) = 1

    def test_high_price(self):
        assert calculate_slippage(99) == 1

    def test_low_depth_adds_slippage(self):
        no_depth = calculate_slippage(50, ask_depth=None)
        low_depth = calculate_slippage(50, ask_depth=2)
        assert low_depth > no_depth

    def test_zero_depth(self):
        slip = calculate_slippage(50, ask_depth=0)
        assert slip > calculate_slippage(50, ask_depth=10)

    def test_high_depth_no_extra(self):
        assert calculate_slippage(50, ask_depth=10) == calculate_slippage(50)
        assert calculate_slippage(50, ask_depth=50) == calculate_slippage(50)


class TestPaperTradeSimulator:
    @pytest.fixture
    def sim(self):
        return PaperTradeSimulator(Portfolio(initial_bankroll_cents=50000))

    def _make_event(self, **overrides):
        base = {
            "confidence_score": 0.8,
            "kalshi_price_at": 40,
            "ask_depth": 20,
            "sport": "nhl",
            "game_event_id": 1,
            "market_id": 1,
        }
        base.update(overrides)
        return base

    def test_open_trade(self, sim: PaperTradeSimulator):
        trade = sim.evaluate_opportunity(self._make_event())
        assert trade is not None
        assert trade["status"] == "open"
        assert trade["entry_price"] == 40
        assert trade["entry_price_adj"] > 40
        assert trade["kelly_size_cents"] > 0

    def test_zero_confidence_rejected(self, sim: PaperTradeSimulator):
        trade = sim.evaluate_opportunity(self._make_event(confidence_score=0))
        assert trade is None

    def test_invalid_price_rejected(self, sim: PaperTradeSimulator):
        assert sim.evaluate_opportunity(self._make_event(kalshi_price_at=0)) is None
        assert sim.evaluate_opportunity(self._make_event(kalshi_price_at=100)) is None
        assert sim.evaluate_opportunity(self._make_event(kalshi_price_at=None)) is None

    def test_opens_no_trade_when_market_overprices_home(self, sim: PaperTradeSimulator):
        trade = sim.evaluate_opportunity(
            self._make_event(
                kalshi_price_at=70,
                baseline_prob=0.40,
                fair_prob_yes=0.40,
            )
        )
        assert trade is not None
        assert trade["side"] == "no"
        assert trade["entry_price"] == 30

    def test_no_trade_uses_no_ask_and_no_depth(self, sim: PaperTradeSimulator):
        trade = sim.evaluate_opportunity(
            self._make_event(
                kalshi_price_at=70,
                fair_prob_yes=0.40,
                kalshi_no_ask=32,
                ask_depth=25,
                kalshi_no_ask_depth=3,
            )
        )
        assert trade is not None
        assert trade["side"] == "no"
        assert trade["entry_price"] == 32
        assert trade["slippage_cents"] == calculate_slippage(32, ask_depth=3)

    def test_trade_carries_market_source(self, sim: PaperTradeSimulator):
        trade = sim.evaluate_opportunity(self._make_event(market_source="kalshi_demo"))
        assert trade is not None
        assert trade["market_source"] == "kalshi_demo"

    def test_trade_uses_market_labels_in_reasoning(self, sim: PaperTradeSimulator):
        trade = sim.evaluate_opportunity(
            self._make_event(
                market_category="total",
                market_label_yes="Over 219.5",
                market_label_no="Under 219.5",
            )
        )
        assert trade is not None
        assert trade["market_category"] == "total"
        assert "taking Over 219.5" in trade["reasoning"]

    def test_portfolio_full_rejected(self):
        sim = PaperTradeSimulator(Portfolio(initial_bankroll_cents=50000, max_positions=1))
        sim.evaluate_opportunity(self._make_event())
        trade2 = sim.evaluate_opportunity(self._make_event())
        assert trade2 is None

    def test_resolve_win(self, sim: PaperTradeSimulator):
        trade = sim.evaluate_opportunity(self._make_event())
        resolved = sim.resolve_trade(trade, exit_price=100, won=True)
        assert resolved["status"] == "resolved_win"
        assert resolved["pnl_cents"] > 0

    def test_resolve_loss(self, sim: PaperTradeSimulator):
        trade = sim.evaluate_opportunity(self._make_event())
        resolved = sim.resolve_trade(trade, exit_price=0, won=False)
        assert resolved["status"] == "resolved_loss"
        assert resolved["pnl_cents"] < 0

    def test_resolve_push(self, sim: PaperTradeSimulator):
        trade = sim.evaluate_opportunity(self._make_event())
        resolved = sim.resolve_trade(
            trade,
            exit_price=trade["entry_price_adj"],
            won=False,
            push=True,
        )
        assert resolved["status"] == "resolved_push"
        assert resolved["pnl_cents"] == 0
        assert resolved["resolution"] == "push"

    def test_bankroll_updates_after_resolution(self, sim: PaperTradeSimulator):
        initial = sim.portfolio.bankroll_cents
        trade = sim.evaluate_opportunity(self._make_event())
        sim.resolve_trade(trade, exit_price=100, won=True)
        assert sim.portfolio.bankroll_cents > initial

    def test_position_closed_after_resolution(self, sim: PaperTradeSimulator):
        trade = sim.evaluate_opportunity(self._make_event())
        assert sim.portfolio.open_count == 1
        sim.resolve_trade(trade, exit_price=0, won=False)
        assert sim.portfolio.open_count == 0
