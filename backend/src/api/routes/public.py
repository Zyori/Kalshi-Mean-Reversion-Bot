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
    sources = registry.source_statuses()
    healthy_states = {"ok", "connected"}
    sources_up = sum(1 for v in sources.values() if v in healthy_states)
    sources_total = sum(1 for v in sources.values() if v != "disabled")
    return {
        "alive": True,
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
        "sources_up": sources_up,
        "sources_total": sources_total,
    }
