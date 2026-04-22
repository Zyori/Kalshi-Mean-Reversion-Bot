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


async def test_analysis_summary_includes_mock_bankroll_fields(client: AsyncClient, _authed: str):
    await _login(client, _authed)
    resp = await client.get("/api/analysis/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["starting_bankroll_cents"] == settings.paper_bankroll_start_cents
    assert "current_bankroll_cents" in body
    assert "available_bankroll_cents" in body
    assert "pending_wagers_cents" in body
    assert body["current_bankroll_cents"] == (
        body["starting_bankroll_cents"] + body["total_pnl_cents"]
    )


async def test_analysis_breakdowns_are_available(client: AsyncClient, _authed: str):
    await _login(client, _authed)

    by_event = await client.get("/api/analysis/by-event-type")
    assert by_event.status_code == 200
    assert isinstance(by_event.json(), list)

    by_market = await client.get("/api/analysis/by-market-category")
    assert by_market.status_code == 200
    assert isinstance(by_market.json(), list)
