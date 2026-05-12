"""Shared shapes for soccer edge functions.

EdgeContext carries every piece of in-game state an edge needs to decide
whether to fire. EdgeSignal is what an edge returns when it does fire —
a stable `signal_kind` tag plus the classification the rest of the
pipeline understands, plus a one-line human reason for logs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EdgeSignal:
    signal_kind: str
    classification: str
    reason: str


@dataclass
class EdgeContext:
    event_type: str
    description: str
    home_score: int
    away_score: int
    minute: int
    baseline_prob: float
    is_home_favorite: bool
