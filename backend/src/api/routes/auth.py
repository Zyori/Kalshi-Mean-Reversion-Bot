import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from src.core.security import clear_session, is_authed, issue_session, verify_password

router = APIRouter(prefix="/api/auth")

_WINDOW_SECONDS = 300
_MAX_ATTEMPTS = 10
_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempts_lock = Lock()


def _rate_limit(ip: str) -> None:
    now = time.monotonic()
    with _attempts_lock:
        bucket = _attempts[ip]
        while bucket and now - bucket[0] > _WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too many attempts",
            )
        bucket.append(now)


class LoginBody(BaseModel):
    password: str


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response):
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip)
    if not verify_password(body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid")
    issue_session(response)
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response):
    clear_session(response)
    return {"ok": True}


@router.get("/me")
async def me(request: Request):
    if not is_authed(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthenticated")
    return {"authed": True}
