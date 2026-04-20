from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "sources" in data


async def test_health_sources_initially_not_connected(client: AsyncClient):
    resp = await client.get("/api/health")
    sources = resp.json()["sources"]
    for source in sources.values():
        assert source in ("disconnected", "disabled")
