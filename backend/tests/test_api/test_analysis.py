from pathlib import Path

import bcrypt
import pytest
from httpx import AsyncClient

import src.main as main_module
from src.config import settings
from src.core.database import Base, create_engine, create_session_factory
from src.models.decision import TradeDecision
from src.models.trade import PaperTrade


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
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'analysis-test.db'}"
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
    assert "pushes" in body


async def test_analysis_breakdowns_are_available(client: AsyncClient, _authed: str):
    await _login(client, _authed)

    by_event = await client.get("/api/analysis/by-event-type")
    assert by_event.status_code == 200
    assert isinstance(by_event.json(), list)

    by_market = await client.get("/api/analysis/by-market-category")
    assert by_market.status_code == 200
    assert isinstance(by_market.json(), list)


async def test_analysis_summary_counts_pushes_as_resolved(
    client: AsyncClient,
    _authed: str,
):
    await _login(client, _authed)
    baseline = await client.get("/api/analysis/summary")
    assert baseline.status_code == 200
    before = baseline.json()

    async with main_module.session_factory() as db:
        db.add(
            PaperTrade(
                market_id=1,
                sport="nba",
                market_category="total",
                side="yes",
                entry_price=45,
                entry_price_adj=46,
                slippage_cents=1,
                confidence_score=0.4,
                kelly_fraction=0.025,
                kelly_size_cents=2500,
                status="resolved_push",
                pnl_cents=0,
            )
        )
        await db.commit()

    resp = await client.get("/api/analysis/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pushes"] == before["pushes"] + 1
    assert body["resolved"] == before["resolved"] + 1


async def test_analysis_decision_audits_are_available(
    client: AsyncClient,
    _authed: str,
):
    await _login(client, _authed)
    baseline_skip = await client.get("/api/analysis/skip-reasons")
    assert baseline_skip.status_code == 200
    baseline_skip_rows = {
        (row["market_category"], row["skip_reason"]): row["count"] for row in baseline_skip.json()
    }

    baseline_summary = await client.get("/api/analysis/decision-summary")
    assert baseline_summary.status_code == 200
    baseline_summary_rows = {
        (row["market_category"], row["action"]): row["count"] for row in baseline_summary.json()
    }

    async with main_module.session_factory() as db:
        db.add_all(
            [
                TradeDecision(
                    sport="nba",
                    market_category="spread",
                    action="skipped",
                    skip_reason="below_confidence_threshold",
                ),
                TradeDecision(
                    sport="nba",
                    market_category="spread",
                    action="opened",
                ),
                TradeDecision(
                    sport="nba",
                    market_category="total",
                    action="skipped",
                    skip_reason="duplicate_position",
                ),
            ]
        )
        await db.commit()

    skip_reasons = await client.get("/api/analysis/skip-reasons")
    assert skip_reasons.status_code == 200
    skip_rows = {
        (row["market_category"], row["skip_reason"]): row["count"] for row in skip_reasons.json()
    }
    assert (
        skip_rows[("spread", "below_confidence_threshold")]
        == baseline_skip_rows.get(("spread", "below_confidence_threshold"), 0) + 1
    )
    assert (
        skip_rows[("total", "duplicate_position")]
        == baseline_skip_rows.get(("total", "duplicate_position"), 0) + 1
    )

    decision_summary = await client.get("/api/analysis/decision-summary")
    assert decision_summary.status_code == 200
    summary_rows = {
        (row["market_category"], row["action"]): row["count"] for row in decision_summary.json()
    }
    assert (
        summary_rows[("spread", "opened")] == baseline_summary_rows.get(("spread", "opened"), 0) + 1
    )
    assert (
        summary_rows[("spread", "skipped")]
        == baseline_summary_rows.get(("spread", "skipped"), 0) + 1
    )
    assert (
        summary_rows[("total", "skipped")] == baseline_summary_rows.get(("total", "skipped"), 0) + 1
    )


async def test_findings_create_and_filter_by_sport(client: AsyncClient, _authed: str):
    await _login(client, _authed)

    # Create a soccer finding
    resp = await client.post(
        "/api/insights",
        json={
            "sport": "soccer",
            "title": "Late-game goals overshoot",
            "body": "EPL moneyline reverts within 4 minutes ~70% of the time.",
            "recommendation": "Hold for 4-min window after goals; tighter stop.",
        },
    )
    assert resp.status_code == 200
    created = resp.json()
    assert created["sport"] == "soccer"
    assert created["type"] == "manual_finding"
    assert created["status"] == "active"
    assert created["title"] == "Late-game goals overshoot"

    # And a UFC finding so we can prove the filter excludes the wrong sport
    other = await client.post(
        "/api/insights",
        json={"sport": "ufc", "title": "Round 1 KOs", "body": "Not enough data yet."},
    )
    assert other.status_code == 200

    # Sport filter returns only the matching one
    soccer = await client.get("/api/insights?sport=soccer")
    assert soccer.status_code == 200
    sports = {row["sport"] for row in soccer.json()}
    assert sports == {"soccer"}

    # Listing without filter sees both
    all_resp = await client.get("/api/insights")
    assert all_resp.status_code == 200
    titles = {row["title"] for row in all_resp.json()}
    assert {"Late-game goals overshoot", "Round 1 KOs"}.issubset(titles)


async def test_finding_create_rejects_empty_title(client: AsyncClient, _authed: str):
    await _login(client, _authed)
    resp = await client.post(
        "/api/insights",
        json={"sport": "soccer", "title": "", "body": "something"},
    )
    assert resp.status_code == 422
