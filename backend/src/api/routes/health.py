import time

from fastapi import APIRouter

from src.supervisor import registry

router = APIRouter()

_start_time = time.monotonic()


@router.get("/api/health")
async def health():
    uptime = time.monotonic() - _start_time
    return {
        "status": "ok",
        "uptime_seconds": round(uptime, 1),
        "sources": registry.source_statuses(),
    }
