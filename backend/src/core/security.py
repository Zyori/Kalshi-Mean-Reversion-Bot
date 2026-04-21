import time
from typing import Final

import bcrypt
from fastapi import HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.config import settings

_SESSION_SALT: Final[str] = "lutz.session.v1"


def _serializer() -> URLSafeTimedSerializer:
    if not settings.session_secret:
        raise RuntimeError("SESSION_SECRET is not configured")
    return URLSafeTimedSerializer(settings.session_secret, salt=_SESSION_SALT)


def verify_password(password: str) -> bool:
    if not settings.admin_password_hash:
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            settings.admin_password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def issue_session(response: Response) -> None:
    token = _serializer().dumps({"iat": int(time.time())})
    max_age = settings.session_max_age_days * 24 * 60 * 60
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.is_prod,
        samesite="strict",
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.is_prod,
        samesite="strict",
    )


def _max_age_seconds() -> int:
    return settings.session_max_age_days * 24 * 60 * 60


def _valid_session(token: str | None) -> bool:
    if not token:
        return False
    try:
        _serializer().loads(token, max_age=_max_age_seconds())
        return True
    except (BadSignature, SignatureExpired):
        return False


async def require_auth(request: Request) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if not _valid_session(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthenticated")


def is_authed(request: Request) -> bool:
    return _valid_session(request.cookies.get(settings.session_cookie_name))
