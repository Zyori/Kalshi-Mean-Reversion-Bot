from datetime import UTC, datetime
from pathlib import Path

import bcrypt
import pytest
from httpx import AsyncClient

import src.main as main_module
from src.config import settings
from src.core.database import Base, create_engine, create_session_factory
from src.models.game import Game


@pytest.fixture(autouse=True)
def _authed(monkeypatch: pytest.MonkeyPatch):
    password = "test-password-123"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    monkeypatch.setattr(settings, "admin_password_hash", hashed)
    monkeypatch.setattr(settings, "session_secret", "test-secret-do-not-use-in-prod")
    monkeypatch.setattr(settings, "env", "dev")
    return password


@pytest.fixture(autouse=True)
async def _isolated_session_factory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'games-test.db'}"
    engine = create_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = create_session_factory(engine)
    original_factory = main_module.session_factory
    monkeypatch.setattr("src.main.session_factory", factory)
    try:
        yield factory
    finally:
        await engine.dispose()
        monkeypatch.setattr("src.main.session_factory", original_factory)


async def _login(client: AsyncClient, password: str) -> None:
    resp = await client.post("/api/auth/login", json={"password": password})
    assert resp.status_code == 200


async def test_list_games_dedupes_matchups_and_serializes_utc(
    client: AsyncClient,
    _authed: str,
):
    async with main_module.session_factory() as db:
        db.add_all(
            [
                Game(
                    sport="mlb",
                    away_team="Milwaukee Brewers",
                    home_team="Detroit Tigers",
                    start_time=datetime(2026, 4, 22, 22, 40),
                    status="scheduled",
                    opening_line_home_prob=0.57,
                ),
                Game(
                    sport="mlb",
                    away_team="Milwaukee Brewers",
                    home_team="Detroit Tigers",
                    start_time=datetime(2026, 4, 22, 22, 41, tzinfo=UTC),
                    status="STATUS_IN_PROGRESS",
                    espn_id="401815044",
                    latest_away_score=2,
                    latest_home_score=1,
                ),
            ]
        )
        await db.commit()

    await _login(client, _authed)
    resp = await client.get("/api/games?days_ahead=1&limit=20")
    assert resp.status_code == 200
    body = resp.json()

    matchups = [
        game
        for game in body
        if game["away_team"] == "Milwaukee Brewers" and game["home_team"] == "Detroit Tigers"
    ]
    assert len(matchups) == 1
    assert matchups[0]["status"] == "STATUS_IN_PROGRESS"
    assert matchups[0]["espn_id"] == "401815044"
    assert matchups[0]["opening_line_home_prob"] == pytest.approx(0.57)
    assert matchups[0]["start_time"].endswith("+00:00")
