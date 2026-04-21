from src.ingestion.kalshi_rest import KalshiRestClient


async def test_get_active_game_markets_uses_ttl_cache() -> None:
    client = object.__new__(KalshiRestClient)
    client.market_cache_ttl_s = 300.0
    client._active_market_cache = {}

    calls = 0

    async def fake_get_events(**_kwargs):
        nonlocal calls
        calls += 1
        return {
            "events": [
                {
                    "event_ticker": "KXMLBGAME-TEST",
                    "title": "Astros vs Guardians Winner?",
                    "markets": [
                        {
                            "ticker": "KXMLBGAME-TEST-CLE",
                            "title": "Astros vs Guardians Winner?",
                            "status": "active",
                            "yes_sub_title": "Guardians",
                            "close_time": "2026-04-21T23:00:00Z",
                            "expiration_time": "2026-04-21T23:00:00Z",
                            "expected_expiration_time": "2026-04-21T23:00:00Z",
                        }
                    ],
                }
            ]
        }

    client.get_events = fake_get_events

    first = await KalshiRestClient.get_active_game_markets(client, "mlb")
    second = await KalshiRestClient.get_active_game_markets(client, "mlb")

    assert len(first) == 1
    assert second == first
    assert calls == 1
