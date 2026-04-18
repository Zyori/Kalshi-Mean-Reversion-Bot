from src.core.logging import get_logger

logger = get_logger(__name__)


class Portfolio:
    def __init__(
        self,
        initial_bankroll_cents: int = 50000,
        max_positions: int = 15,
    ) -> None:
        self.bankroll_cents = initial_bankroll_cents
        self.max_positions = max_positions
        self._open_positions: dict[int, int] = {}

    @property
    def open_count(self) -> int:
        return len(self._open_positions)

    @property
    def pending_wagers_cents(self) -> int:
        return sum(self._open_positions.values())

    @property
    def available_cents(self) -> int:
        return self.bankroll_cents - self.pending_wagers_cents

    def can_open(self) -> bool:
        return self.open_count < self.max_positions and self.available_cents > 0

    def open_position(self, trade_id: int, size_cents: int) -> None:
        if not self.can_open():
            logger.warning("portfolio_cannot_open", trade_id=trade_id)
            return
        self._open_positions[trade_id] = size_cents
        logger.info(
            "position_opened",
            trade_id=trade_id,
            size_cents=size_cents,
            open_count=self.open_count,
            available=self.available_cents,
        )

    def close_position(self, trade_id: int, pnl_cents: int) -> None:
        wager = self._open_positions.pop(trade_id, None)
        if wager is None:
            logger.warning("position_not_found", trade_id=trade_id)
            return
        self.bankroll_cents += pnl_cents
        logger.info(
            "position_closed",
            trade_id=trade_id,
            pnl_cents=pnl_cents,
            bankroll=self.bankroll_cents,
            open_count=self.open_count,
        )
