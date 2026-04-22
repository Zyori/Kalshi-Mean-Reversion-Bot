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


async def test_strategy_catalog_exposes_live_policy(
    client: AsyncClient,
    _authed: str,
):
    await _login(client, _authed)
    resp = await client.get("/api/strategy")
    assert resp.status_code == 200
    body = resp.json()

    assert body["platform_timezone"] == "America/New_York"
    assert body["trade_policy"]["paper_bankroll_start_cents"] == 100000
    assert body["trade_policy"]["max_open_per_market"] == 3

    markets = {entry["market_category"]: entry for entry in body["trade_policy"]["markets"]}
    assert set(markets) == {"moneyline", "spread", "total", "team_total"}
    assert markets["team_total"]["confidence_threshold"] == markets["total"]["confidence_threshold"]
    assert markets["team_total"]["deviation_threshold"] == markets["total"]["deviation_threshold"]

    sports = {entry["sport"]: entry for entry in body["sports"]}
    assert "nba" in sports
    assert sports["nba"]["moneyline"]["params"]["min_favorite_prob"] == 0.60
    team_total = next(
        market
        for market in sports["mlb"]["markets"]
        if market["market_category"] == "team_total"
    )
    assert team_total["candidate_edge_min"] == 0.5
    assert team_total["candidate_edge_max"] == 2.0
