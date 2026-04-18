import asyncio
from collections import defaultdict
from dataclasses import dataclass, field

from src.core.logging import get_logger

logger = get_logger(__name__)

MAX_WINDOW = 100


@dataclass
class TradeRecord:
    sport: str
    event_type: str
    won: bool
    pnl_cents: int
    confidence_score: float


@dataclass
class BucketStats:
    trades: list[TradeRecord] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for t in self.trades if t.won)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        return self.wins / self.count

    @property
    def total_pnl(self) -> int:
        return sum(t.pnl_cents for t in self.trades)

    @property
    def mean_pnl(self) -> float:
        if not self.trades:
            return 0.0
        return self.total_pnl / self.count

    @property
    def pnl_values(self) -> list[int]:
        return [t.pnl_cents for t in self.trades]

    def add(self, record: TradeRecord) -> None:
        self.trades.append(record)
        if len(self.trades) > MAX_WINDOW:
            self.trades = self.trades[-MAX_WINDOW:]


class Accumulators:
    def __init__(self) -> None:
        self._by_sport: dict[str, BucketStats] = defaultdict(BucketStats)
        self._by_event_type: dict[str, BucketStats] = defaultdict(BucketStats)
        self._overall = BucketStats()

    def update(self, record: TradeRecord) -> None:
        self._overall.add(record)
        self._by_sport[record.sport].add(record)
        self._by_event_type[record.event_type].add(record)

    async def update_async(self, record: TradeRecord) -> None:
        await asyncio.to_thread(self.update, record)

    def summary(self) -> dict:
        return {
            "overall": _bucket_to_dict(self._overall),
            "by_sport": {k: _bucket_to_dict(v) for k, v in self._by_sport.items()},
            "by_event_type": {k: _bucket_to_dict(v) for k, v in self._by_event_type.items()},
        }

    def get_sport_stats(self, sport: str) -> BucketStats:
        return self._by_sport[sport]

    def get_event_type_stats(self, event_type: str) -> BucketStats:
        return self._by_event_type[event_type]


def _bucket_to_dict(bucket: BucketStats) -> dict:
    return {
        "count": bucket.count,
        "wins": bucket.wins,
        "win_rate": round(bucket.win_rate, 4),
        "total_pnl_cents": bucket.total_pnl,
        "mean_pnl_cents": round(bucket.mean_pnl, 2),
    }
