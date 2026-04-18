import asyncio
import time
from typing import Any

import httpx

from src.config import settings
from src.core.auth import KalshiAuth
from src.core.exceptions import IngestionError
from src.core.logging import get_logger
from src.core.types import KALSHI_URLS

logger = get_logger(__name__)


class TokenBucket:
    def __init__(self, rate: float, capacity: int) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    async def acquire(self) -> None:
        while True:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return
            wait = (1.0 - self.tokens) / self.rate
            await asyncio.sleep(wait)


class KalshiRestClient:
    def __init__(self) -> None:
        env = settings.kalshi_environment
        urls = KALSHI_URLS[env]
        self.base_url = urls["rest"]

        self.auth = KalshiAuth(settings.kalshi_key_id, settings.kalshi_private_key_path)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=self.auth,
            timeout=15.0,
            headers={"Accept": "application/json"},
        )
        self.rate_limiter = TokenBucket(rate=8.0, capacity=10)

    async def close(self) -> None:
        await self.client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        await self.rate_limiter.acquire()
        try:
            resp = await self.client.request(method, path, **kwargs)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "2"))
                logger.warning("rate_limited", retry_after=retry_after, path=path)
                await asyncio.sleep(retry_after)
                return await self._request(method, path, **kwargs)

            resp.raise_for_status()
            return resp.json()

        except httpx.HTTPStatusError as e:
            logger.error("kalshi_api_error", status=e.response.status_code, path=path)
            raise IngestionError(f"Kalshi API {e.response.status_code}: {path}") from e
        except httpx.RequestError as e:
            logger.error("kalshi_network_error", path=path, error=str(e))
            raise IngestionError(f"Kalshi network error: {path}") from e

    async def get_markets(
        self,
        event_ticker: str | None = None,
        status: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {"limit": limit}
        if event_ticker:
            params["event_ticker"] = event_ticker
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        return await self._request("GET", "/markets", params=params)

    async def get_market(self, ticker: str) -> dict:
        return await self._request("GET", f"/markets/{ticker}")

    async def get_orderbook(self, ticker: str, depth: int = 5) -> dict:
        return await self._request("GET", f"/markets/{ticker}/orderbook", params={"depth": depth})

    async def get_event(self, event_ticker: str) -> dict:
        return await self._request("GET", f"/events/{event_ticker}")

    async def get_balance(self) -> dict:
        return await self._request("GET", "/portfolio/balance")
