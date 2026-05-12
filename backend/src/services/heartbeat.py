"""Per-loop heartbeat tracking — the single source of truth for "is the
supervisor actually doing work, or just silently throwing exceptions?"

V1's supervisor failed for 18 days without anyone noticing, because the
process was still running but every odds-loop tick was hitting a DB lock.
Every long-lived loop in the supervisor now reports tick / success / error
to `loop_heartbeats`, and the health endpoints surface staleness so the
next silent failure surfaces in seconds rather than weeks.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class LoopHeartbeat:
    """Liveness record for one supervisor loop."""

    name: str
    expected_interval_s: float
    last_tick_at: float | None = None
    last_success_at: float | None = None
    last_error_at: float | None = None
    last_error_message: str | None = None
    tick_count: int = 0
    success_count: int = 0
    error_count: int = 0

    def tick(self) -> None:
        self.last_tick_at = time.time()
        self.tick_count += 1

    def success(self) -> None:
        self.last_success_at = time.time()
        self.success_count += 1

    def error(self, exc: BaseException) -> None:
        self.last_error_at = time.time()
        self.last_error_message = f"{type(exc).__name__}: {exc}"
        self.error_count += 1

    def staleness_seconds(self) -> float | None:
        if self.last_tick_at is None:
            return None
        return time.time() - self.last_tick_at

    def is_stale(self) -> bool:
        """True if no tick has happened in 3x the expected interval.

        3x is forgiving enough that ordinary jitter (network retries, lock
        waits) doesn't trigger false alarms, but tight enough that real
        wedge-states surface inside a few minutes for most loops.
        """
        s = self.staleness_seconds()
        if s is None:
            return True
        return s > (self.expected_interval_s * 3)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "expected_interval_s": self.expected_interval_s,
            "last_tick_at": self.last_tick_at,
            "last_success_at": self.last_success_at,
            "last_error_at": self.last_error_at,
            "last_error_message": self.last_error_message,
            "tick_count": self.tick_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "staleness_seconds": self.staleness_seconds(),
            "stale": self.is_stale(),
        }


@dataclass
class HeartbeatRegistry:
    """Process-wide collection of supervisor loop heartbeats."""

    loops: dict[str, LoopHeartbeat] = field(default_factory=dict)

    def register(self, name: str, expected_interval_s: float) -> LoopHeartbeat:
        hb = LoopHeartbeat(name=name, expected_interval_s=expected_interval_s)
        self.loops[name] = hb
        return hb

    def get(self, name: str) -> LoopHeartbeat | None:
        return self.loops.get(name)

    def any_stale(self) -> bool:
        return any(hb.is_stale() for hb in self.loops.values())

    def to_list(self) -> list[dict]:
        return [hb.to_dict() for hb in self.loops.values()]
