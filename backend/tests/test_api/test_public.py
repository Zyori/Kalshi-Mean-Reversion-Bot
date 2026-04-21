from httpx import AsyncClient


async def test_heartbeat_is_public(client: AsyncClient):
    resp = await client.get("/api/public/heartbeat")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert isinstance(body["timestamp"], int)


async def test_status_is_public(client: AsyncClient):
    resp = await client.get("/api/public/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["alive"] is True
    assert isinstance(body["uptime_seconds"], (int, float))
    assert isinstance(body["sources_up"], int)
    assert isinstance(body["sources_total"], int)


async def test_status_does_not_leak_trade_data(client: AsyncClient):
    resp = await client.get("/api/public/status")
    body = resp.json()
    forbidden_keys = {"trades", "games", "pnl", "balance", "positions", "markets"}
    assert not forbidden_keys.intersection(body.keys())
