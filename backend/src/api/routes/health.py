import time

from fastapi import APIRouter

router = APIRouter()

_start_time = time.monotonic()


@router.get("/api/health")
async def health():
    uptime = time.monotonic() - _start_time
    return {
        "status": "ok",
        "uptime_seconds": round(uptime, 1),
        "sources": {
            "kalshi_ws": "disconnected",
            "espn_scoreboard": "disconnected",
            "espn_events": "disconnected",
            "odds_api": "disconnected",
        },
    }
