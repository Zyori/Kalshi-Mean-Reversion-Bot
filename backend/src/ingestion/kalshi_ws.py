import asyncio
import contextlib
import json
import time
from typing import TYPE_CHECKING

import websockets

from src.config import settings
from src.core.auth import KalshiAuth
from src.core.exceptions import IngestionError
from src.core.logging import get_logger
from src.core.types import KALSHI_URLS

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

logger = get_logger(__name__)

STALENESS_TIMEOUT_S = 30.0
BACKOFF_BASE_S = 1.0
BACKOFF_MAX_S = 30.0
BATCH_SIZE = 100


class KalshiWsClient:
    def __init__(self, queue: asyncio.Queue) -> None:
        env = settings.kalshi_environment
        self.ws_url = KALSHI_URLS[env]["ws"]
        self.auth = KalshiAuth(settings.kalshi_key_id, settings.kalshi_private_key_path)
        self.queue = queue

        self._ws: ClientConnection | None = None
        self._subscriptions: dict[str, list[str]] = {}
        self._sequence_numbers: dict[int, int] = {}
        self._last_message_at: float = 0.0
        self._status: str = "disconnected"

    @property
    def status(self) -> str:
        if self._status == "connected" and self._is_stale():
            return "stale"
        return self._status

    def _is_stale(self) -> bool:
        if self._last_message_at == 0.0:
            return False
        return (time.monotonic() - self._last_message_at) > STALENESS_TIMEOUT_S

    def _make_auth_headers(self) -> dict[str, str]:
        timestamp_ms = str(int(time.time() * 1000))
        signature = self.auth._sign(timestamp_ms, "GET", "/trade-api/ws/v2")
        return {
            "KALSHI-ACCESS-KEY": self.auth.key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": signature,
        }

    async def connect(self) -> None:
        headers = self._make_auth_headers()
        self._ws = await websockets.connect(self.ws_url, additional_headers=headers)
        self._status = "connected"
        self._last_message_at = time.monotonic()
        self._sequence_numbers.clear()
        logger.info("kalshi_ws_connected", url=self.ws_url)
        await self._replay_subscriptions()

    async def subscribe(self, channel: str, market_tickers: list[str]) -> None:
        key = f"{channel}:{','.join(sorted(market_tickers))}"
        self._subscriptions[key] = market_tickers

        if self._ws:
            await self._send_subscribe(channel, market_tickers)

    async def _send_subscribe(self, channel: str, market_tickers: list[str]) -> None:
        if not self._ws:
            return

        for i in range(0, max(len(market_tickers), 1), BATCH_SIZE):
            batch = market_tickers[i : i + BATCH_SIZE]
            msg: dict = {
                "id": int(time.time() * 1000) + i,
                "cmd": "subscribe",
                "params": {"channels": [channel]},
            }
            if batch:
                msg["params"]["market_tickers"] = batch
            await self._ws.send(json.dumps(msg))

        logger.info("kalshi_ws_subscribed", channel=channel, ticker_count=len(market_tickers))

    async def _replay_subscriptions(self) -> None:
        for key, tickers in self._subscriptions.items():
            channel = key.split(":")[0]
            await self._send_subscribe(channel, tickers)

    async def _enqueue(self, data: dict) -> None:
        if self.queue.full():
            with contextlib.suppress(asyncio.QueueEmpty):
                self.queue.get_nowait()
            logger.warning("kalshi_ws_queue_overflow", qsize=self.queue.qsize())
        await self.queue.put(data)

    def _check_sequence(self, msg: dict) -> None:
        sid = msg.get("sid")
        seq = msg.get("seq")
        if sid is None or seq is None:
            return

        last = self._sequence_numbers.get(sid)
        if last is not None and seq > last + 1:
            gap = seq - last - 1
            if gap > 10:
                logger.warning(
                    "kalshi_ws_sequence_gap",
                    sid=sid,
                    expected=last + 1,
                    got=seq,
                    gap=gap,
                )
        self._sequence_numbers[sid] = seq

    async def listen(self) -> None:
        if not self._ws:
            raise IngestionError("WebSocket not connected")

        async for raw in self._ws:
            self._last_message_at = time.monotonic()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("kalshi_ws_invalid_json")
                continue

            msg_type = data.get("type")
            if msg_type in ("orderbook_snapshot", "orderbook_delta"):
                self._check_sequence(data)
                await self._enqueue(data)
            elif msg_type == "error":
                logger.error("kalshi_ws_server_error", msg=data)

    async def close(self) -> None:
        self._status = "disconnected"
        if self._ws:
            await self._ws.close()
            self._ws = None


async def kalshi_ws_consumer(queue: asyncio.Queue) -> None:
    client = KalshiWsClient(queue)
    attempt = 0

    while True:
        try:
            await client.connect()
            attempt = 0
            await client.listen()
        except websockets.ConnectionClosed as e:
            logger.warning("kalshi_ws_closed", code=e.code, reason=str(e.reason))
        except Exception:
            logger.exception("kalshi_ws_error")
        finally:
            client._status = "disconnected"

        delay = min(BACKOFF_BASE_S * (2**attempt), BACKOFF_MAX_S)
        attempt += 1
        logger.info("kalshi_ws_reconnecting", attempt=attempt, delay_s=round(delay, 1))
        await asyncio.sleep(delay)
