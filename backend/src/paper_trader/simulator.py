from typing import Any

from src.core.logging import get_logger
from src.paper_trader.kelly import ConservativeEstimator, ProbabilityEstimator, kelly_size
from src.paper_trader.portfolio import Portfolio

logger = get_logger(__name__)

FLAT_BET_CENTS = 500


def calculate_slippage(entry_price_cents: int, ask_depth: int | None = None) -> int:
    base = max(1, int(entry_price_cents * 0.005))
    if ask_depth is not None and ask_depth < 10:
        shortfall = 10 - ask_depth
        base += (shortfall // 5) + 1
    return base


class PaperTradeSimulator:
    def __init__(
        self,
        portfolio: Portfolio | None = None,
        estimator: ProbabilityEstimator | None = None,
    ) -> None:
        self.portfolio = portfolio or Portfolio()
        self.estimator = estimator or ConservativeEstimator()
        self._trade_counter = 0

    def evaluate_opportunity(self, event: dict[str, Any]) -> dict[str, Any] | None:
        if not self.portfolio.can_open():
            return None

        confidence = event.get("confidence_score", 0.0)
        if confidence <= 0:
            return None

        kalshi_price = event.get("kalshi_price_at")
        if not kalshi_price or kalshi_price <= 0 or kalshi_price >= 100:
            return None

        p = self.estimator.estimate(confidence, event)
        ask_depth = event.get("ask_depth")
        slippage = calculate_slippage(kalshi_price, ask_depth)
        entry_adj = kalshi_price + slippage

        size = kelly_size(
            p=p,
            entry_price_cents=entry_adj,
            bankroll_cents=self.portfolio.bankroll_cents,
            pending_wagers_cents=self.portfolio.pending_wagers_cents,
        )

        if size == 0:
            return None

        f = kelly_size(
            p=p,
            entry_price_cents=entry_adj,
            bankroll_cents=self.portfolio.bankroll_cents,
            pending_wagers_cents=self.portfolio.pending_wagers_cents,
            fraction_multiplier=1.0,
        )

        self._trade_counter += 1
        trade = {
            "id": self._trade_counter,
            "sport": event.get("sport"),
            "side": "yes",
            "entry_price": kalshi_price,
            "entry_price_adj": entry_adj,
            "slippage_cents": slippage,
            "confidence_score": confidence,
            "kelly_fraction": round(f / self.portfolio.bankroll_cents, 4) if f > 0 else 0.0,
            "kelly_size_cents": size,
            "flat_size_cents": FLAT_BET_CENTS,
            "status": "open",
            "game_event_id": event.get("game_event_id"),
            "market_id": event.get("market_id"),
            "game_context": event,
        }

        self.portfolio.open_position(self._trade_counter, size)

        logger.info(
            "paper_trade_opened",
            trade_id=self._trade_counter,
            sport=trade["sport"],
            entry=entry_adj,
            size=size,
            confidence=confidence,
        )

        return trade

    def resolve_trade(self, trade: dict[str, Any], exit_price: int, won: bool) -> dict[str, Any]:
        entry_adj = trade["entry_price_adj"]
        kelly_size_cents = trade["kelly_size_cents"]
        flat_size_cents = trade["flat_size_cents"]

        if won:
            payout_per_contract = 100 - entry_adj
            pnl_cents = int((kelly_size_cents / entry_adj) * payout_per_contract)
            pnl_flat = int((flat_size_cents / entry_adj) * payout_per_contract)
            status = "resolved_win"
        else:
            pnl_cents = -kelly_size_cents
            pnl_flat = -flat_size_cents
            status = "resolved_loss"

        trade["exit_price"] = exit_price
        trade["pnl_cents"] = pnl_cents
        trade["pnl_kelly_cents"] = pnl_cents
        trade["pnl_flat_cents"] = pnl_flat
        trade["status"] = status
        trade["resolution"] = "yes" if won else "no"

        self.portfolio.close_position(trade["id"], pnl_cents)

        logger.info(
            "paper_trade_resolved",
            trade_id=trade["id"],
            status=status,
            pnl_cents=pnl_cents,
            bankroll=self.portfolio.bankroll_cents,
        )

        return trade
