import pytest
from httpx import AsyncClient

from src.supervisor import registry


@pytest.mark.parametrize(
    ("statuses", "expected_up", "expected_total"),
    [
        (
            {
                "kalshi_ws": "disabled",
                "espn_scoreboard": "connected",
                "espn_events": "disconnected",
                "odds_api": "connected",
            },
            2,
            3,
        ),
        (
            {
                "kalshi_ws": "disabled",
                "espn_scoreboard": "ok",
                "espn_events": "disabled",
                "odds_api": "disconnected",
            },
            1,
            2,
        ),
    ],
)
async def test_public_status_counts_connected_sources_as_up(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    statuses: dict[str, str],
    expected_up: int,
    expected_total: int,
):
    monkeypatch.setattr(registry, "source_statuses", lambda: statuses)
    resp = await client.get("/api/public/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sources_up"] == expected_up
    assert body["sources_total"] == expected_total
