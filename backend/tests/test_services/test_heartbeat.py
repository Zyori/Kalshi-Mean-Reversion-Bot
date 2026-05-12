"""Heartbeat contract tests — the single mechanism guarding against silent
supervisor failures."""

import time

from src.services.heartbeat import HeartbeatRegistry, LoopHeartbeat


def test_fresh_heartbeat_has_no_ticks_and_is_stale():
    hb = LoopHeartbeat(name="scoreboard", expected_interval_s=10.0)
    assert hb.last_tick_at is None
    # A loop that has never ticked is stale by definition — better to alarm
    # eagerly on startup than miss a never-started loop.
    assert hb.is_stale()
    assert hb.tick_count == 0


def test_tick_marks_recent():
    hb = LoopHeartbeat(name="scoreboard", expected_interval_s=10.0)
    hb.tick()
    assert hb.tick_count == 1
    assert hb.is_stale() is False
    assert hb.staleness_seconds() is not None
    assert hb.staleness_seconds() < 1.0


def test_success_records_separately_from_tick():
    hb = LoopHeartbeat(name="scoreboard", expected_interval_s=10.0)
    hb.tick()
    hb.success()
    assert hb.success_count == 1
    assert hb.error_count == 0


def test_error_records_message_and_increments_count():
    hb = LoopHeartbeat(name="odds", expected_interval_s=60.0)
    hb.tick()
    try:
        raise ValueError("database is locked")
    except ValueError as e:
        hb.error(e)
    assert hb.error_count == 1
    assert hb.last_error_message == "ValueError: database is locked"


def test_stale_after_three_intervals():
    hb = LoopHeartbeat(name="snapshot", expected_interval_s=10.0)
    hb.tick()
    # Backdate the tick to 31s ago (>3 * 10s).
    hb.last_tick_at = time.time() - 31.0
    assert hb.is_stale()


def test_not_stale_within_three_intervals():
    hb = LoopHeartbeat(name="snapshot", expected_interval_s=10.0)
    hb.tick()
    hb.last_tick_at = time.time() - 25.0  # 2.5x interval — still healthy
    assert hb.is_stale() is False


def test_registry_any_stale_flags_silent_failures():
    reg = HeartbeatRegistry()
    healthy = reg.register("scoreboard", 10.0)
    silent = reg.register("odds", 60.0)
    healthy.tick()
    silent.tick()
    silent.last_tick_at = time.time() - 3600  # an hour of silence
    assert reg.any_stale()


def test_registry_to_list_exposes_all_loops():
    reg = HeartbeatRegistry()
    reg.register("scoreboard", 10.0)
    reg.register("odds", 60.0)
    names = {entry["name"] for entry in reg.to_list()}
    assert names == {"scoreboard", "odds"}
