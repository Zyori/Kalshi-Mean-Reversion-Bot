import bcrypt
import pytest
from httpx import AsyncClient

from src.config import settings
from src.core.database import Base
from src.main import engine, session_factory
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
async def _ensure_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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

    async with session_factory() as db:
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
        (row["market_category"], row["skip_reason"]): row["count"]
        for row in baseline_skip.json()
    }

    baseline_summary = await client.get("/api/analysis/decision-summary")
    assert baseline_summary.status_code == 200
    baseline_summary_rows = {
        (row["market_category"], row["action"]): row["count"]
        for row in baseline_summary.json()
    }

    async with session_factory() as db:
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
        (row["market_category"], row["skip_reason"]): row["count"]
        for row in skip_reasons.json()
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
        (row["market_category"], row["action"]): row["count"]
        for row in decision_summary.json()
    }
    assert (
        summary_rows[("spread", "opened")]
        == baseline_summary_rows.get(("spread", "opened"), 0) + 1
    )
    assert (
        summary_rows[("spread", "skipped")]
        == baseline_summary_rows.get(("spread", "skipped"), 0) + 1
    )
    assert (
        summary_rows[("total", "skipped")]
        == baseline_summary_rows.get(("total", "skipped"), 0) + 1
    )
