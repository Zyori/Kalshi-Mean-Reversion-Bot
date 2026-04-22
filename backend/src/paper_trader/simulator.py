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


def _build_reasoning(
    *,
    event: dict[str, Any],
    side: str,
    fair_prob_yes: float,
    market_prob_yes: float,
    entry_price: int,
    size_cents: int,
) -> str:
    event_type = event.get("event_type") or "event"
    classification = event.get("classification") or "unclassified"
    market_source = event.get("market_source") or "unknown"
    market_category = event.get("market_category") or "moneyline"
    yes_label = event.get("market_label_yes") or "YES"
    no_label = event.get("market_label_no") or "NO"
    selected_team = yes_label if side == "yes" else no_label
    deviation = event.get("deviation")
    deviation_text = f"{deviation:.3f}" if isinstance(deviation, (int, float)) else "n/a"
    return (
        f"Mean reversion {side.upper()} off {classification}: "
        f"market={market_category}, yes_contract={yes_label}, pick={selected_team}, "
        f"fair_yes={fair_prob_yes:.3f}, market_yes={market_prob_yes:.3f}, "
        f"deviation={deviation_text}, event={event_type}, source={market_source}, "
        f"entry={entry_price}c, wager={size_cents}c"
    )


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

        yes_market_price = event.get("kalshi_price_at")
        if not yes_market_price or yes_market_price <= 0 or yes_market_price >= 100:
            return None

        fair_prob_yes = event.get("fair_prob_yes", event.get("baseline_prob", 0.5))
        market_prob_yes = yes_market_price / 100.0
        side = "yes" if fair_prob_yes >= market_prob_yes else "no"
        contract_prob = fair_prob_yes if side == "yes" else 1.0 - fair_prob_yes
        entry_price = (
            event.get("kalshi_yes_ask", yes_market_price)
            if side == "yes"
            else event.get("kalshi_no_ask", 100 - yes_market_price)
        )
        ask_depth = (
            event.get("kalshi_yes_ask_depth", event.get("ask_depth"))
            if side == "yes"
            else event.get("kalshi_no_ask_depth", event.get("ask_depth"))
        )

        if contract_prob <= 0 or contract_prob >= 1:
            return None

        slippage = calculate_slippage(entry_price, ask_depth)
        entry_adj = min(99, entry_price + slippage)

        size = kelly_size(
            p=contract_prob,
            entry_price_cents=entry_adj,
            bankroll_cents=self.portfolio.bankroll_cents,
            pending_wagers_cents=self.portfolio.pending_wagers_cents,
        )

        if size == 0:
            return None

        f = kelly_size(
            p=contract_prob,
            entry_price_cents=entry_adj,
            bankroll_cents=self.portfolio.bankroll_cents,
            pending_wagers_cents=self.portfolio.pending_wagers_cents,
            fraction_multiplier=1.0,
        )

        self._trade_counter += 1
        trade = {
            "id": self._trade_counter,
            "sport": event.get("sport"),
            "market_category": event.get("market_category", "moneyline"),
            "side": side,
            "entry_price": entry_price,
            "entry_price_adj": entry_adj,
            "slippage_cents": slippage,
            "confidence_score": confidence,
            "kelly_fraction": round(f / self.portfolio.bankroll_cents, 4) if f > 0 else 0.0,
            "kelly_size_cents": size,
            "flat_size_cents": FLAT_BET_CENTS,
            "status": "open",
            "game_event_id": event.get("game_event_id"),
            "market_id": event.get("market_id"),
            "market_source": event.get("market_source"),
            "fair_prob_yes": fair_prob_yes,
            "yes_price_at_entry": yes_market_price,
            "game_context": event,
            "reasoning": _build_reasoning(
                event=event,
                side=side,
                fair_prob_yes=fair_prob_yes,
                market_prob_yes=market_prob_yes,
                entry_price=entry_price,
                size_cents=size,
            ),
        }

        self.portfolio.open_position(self._trade_counter, size)

        logger.info(
            "paper_trade_opened",
            trade_id=self._trade_counter,
            sport=trade["sport"],
            market_category=trade["market_category"],
            entry=entry_adj,
            size=size,
            confidence=confidence,
        )

        return trade

    def resolve_trade(
        self,
        trade: dict[str, Any],
        exit_price: int,
        won: bool,
        *,
        push: bool = False,
    ) -> dict[str, Any]:
        entry_adj = trade["entry_price_adj"]
        kelly_size_cents = trade["kelly_size_cents"]
        flat_size_cents = trade["flat_size_cents"]

        if push:
            pnl_cents = 0
            pnl_flat = 0
            status = "resolved_push"
        elif won:
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
        if push:
            trade["resolution"] = "push"
        else:
            trade["resolution"] = (
                trade["side"] if won else ("no" if trade["side"] == "yes" else "yes")
            )

        self.portfolio.close_position(trade["id"], pnl_cents)

        logger.info(
            "paper_trade_resolved",
            trade_id=trade["id"],
            status=status,
            pnl_cents=pnl_cents,
            bankroll=self.portfolio.bankroll_cents,
        )

        return trade
