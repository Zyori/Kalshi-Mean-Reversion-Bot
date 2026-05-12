import time

from fastapi import APIRouter

from src.supervisor import registry

router = APIRouter(prefix="/api/public")

_start_time = time.monotonic()


@router.get("/heartbeat")
async def heartbeat():
    return {"ok": True, "timestamp": int(time.time())}


@router.get("/status")
async def status():
    """Public, low-detail status — counts only, no internal labels.

    Surfaces enough for a public uptime check (alive / number of loops healthy)
    without leaking which exact sources are configured.
    """
    sources = registry.source_statuses()
    healthy_states = {"ok", "connected"}
    sources_up = sum(1 for v in sources.values() if v in healthy_states)
    sources_total = sum(1 for v in sources.values() if v != "disabled")

    loops = registry.heartbeats.to_list()
    loops_total = len(loops)
    loops_healthy = sum(1 for hb in loops if not hb["stale"])

    return {
        "alive": True,
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
        "sources_up": sources_up,
        "sources_total": sources_total,
        "loops_healthy": loops_healthy,
        "loops_total": loops_total,
    }
