import time

from fastapi import APIRouter

from src.supervisor import registry

router = APIRouter()

_start_time = time.monotonic()


@router.get("/api/health")
async def health():
    """Authenticated health surface — full detail including per-loop heartbeats.

    A loop is `stale` if its last tick was longer than 3x its expected interval
    ago. Overall status is `degraded` if any loop is stale and `ok` otherwise;
    this is the signal that would have caught v1's 18-day silent failure on
    day one.
    """
    uptime = time.monotonic() - _start_time
    heartbeats = registry.heartbeats.to_list()
    degraded = any(hb["stale"] for hb in heartbeats)
    return {
        "status": "degraded" if degraded else "ok",
        "uptime_seconds": round(uptime, 1),
        "sources": registry.source_statuses(),
        "loops": heartbeats,
    }
