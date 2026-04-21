import bcrypt
import pytest
from httpx import AsyncClient

from src.config import settings


@pytest.fixture(autouse=True)
def _authed(monkeypatch: pytest.MonkeyPatch):
    password = "test-password-123"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    monkeypatch.setattr(settings, "admin_password_hash", hashed)
    monkeypatch.setattr(settings, "session_secret", "test-secret-do-not-use-in-prod")
    monkeypatch.setattr(settings, "env", "dev")
    return password


async def _login(client: AsyncClient, password: str) -> None:
    resp = await client.post("/api/auth/login", json={"password": password})
    assert resp.status_code == 200


async def test_health_returns_ok(client: AsyncClient, _authed: str):
    await _login(client, _authed)
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "sources" in data


async def test_health_sources_initially_not_connected(client: AsyncClient, _authed: str):
    await _login(client, _authed)
    resp = await client.get("/api/health")
    sources = resp.json()["sources"]
    for source in sources.values():
        assert source in ("disconnected", "disabled")
