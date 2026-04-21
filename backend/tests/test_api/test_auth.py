import bcrypt
import pytest
from httpx import AsyncClient

from src.config import settings


@pytest.fixture(autouse=True)
def _auth_settings(monkeypatch: pytest.MonkeyPatch):
    password = "test-password-123"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    monkeypatch.setattr(settings, "admin_password_hash", hashed)
    monkeypatch.setattr(settings, "session_secret", "test-secret-do-not-use-in-prod")
    monkeypatch.setattr(settings, "env", "dev")
    yield password


async def test_login_rejects_wrong_password(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"password": "nope"})
    assert resp.status_code == 401


async def test_login_sets_session_cookie(client: AsyncClient, _auth_settings: str):
    resp = await client.post("/api/auth/login", json={"password": _auth_settings})
    assert resp.status_code == 200
    assert settings.session_cookie_name in resp.cookies


async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_returns_ok_after_login(client: AsyncClient, _auth_settings: str):
    login = await client.post("/api/auth/login", json={"password": _auth_settings})
    assert login.status_code == 200
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json() == {"authed": True}


async def test_logout_clears_session(client: AsyncClient, _auth_settings: str):
    await client.post("/api/auth/login", json={"password": _auth_settings})
    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 200
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_protected_route_requires_auth(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 401


async def test_protected_route_accessible_after_login(client: AsyncClient, _auth_settings: str):
    await client.post("/api/auth/login", json={"password": _auth_settings})
    resp = await client.get("/api/health")
    assert resp.status_code == 200
