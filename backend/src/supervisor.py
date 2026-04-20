import asyncio
from dataclasses import dataclass, field
from typing import Any

from src.analysis.accumulators import Accumulators
from src.core.logging import get_logger
from src.ingestion.espn_events import EspnEventsPoller
from src.ingestion.espn_scoreboard import EspnScoreboardPoller
from src.ingestion.odds import OddsApiPoller
from src.paper_trader.portfolio import Portfolio
from src.paper_trader.simulator import PaperTradeSimulator
from src.strategy.detector import EventDetector

logger = get_logger(__name__)

QUEUE_SIZE = 1000


@dataclass
class ComponentRegistry:
    scoreboard: EspnScoreboardPoller | None = None
    events: EspnEventsPoller | None = None
    odds: OddsApiPoller | None = None
    detector: EventDetector | None = None
    simulator: PaperTradeSimulator | None = None
    accumulators: Accumulators = field(default_factory=Accumulators)

    def source_statuses(self) -> dict[str, str]:
        return {
            "kalshi_ws": "disabled",
            "espn_scoreboard": self.scoreboard.status if self.scoreboard else "disabled",
            "espn_events": self.events.status if self.events else "disabled",
            "odds_api": self.odds.status if self.odds else "disabled",
        }


registry = ComponentRegistry()


async def _scoreboard_loop(
    scoreboard: EspnScoreboardPoller,
    events_poller: EspnEventsPoller,
) -> None:
    while True:
        try:
            updates = await scoreboard.poll_once()
            for update in updates:
                await scoreboard._enqueue(update)
                espn_id = update.get("espn_id")
                sport = update.get("sport")
                status = update.get("status", "")
                if espn_id and sport and status.lower() in ("in_progress", "status_in_progress"):
                    events_poller.watch_game(espn_id, sport)
                elif espn_id and status.lower() in ("final", "status_final", "post"):
                    events_poller.unwatch_game(espn_id)
            if updates:
                logger.info("scoreboard_updates", count=len(updates))
        except Exception:
            logger.exception("scoreboard_loop_error")
        await asyncio.sleep(10.0)


async def _events_loop(events_poller: EspnEventsPoller) -> None:
    while True:
        try:
            new_events = await events_poller.poll_all()
            for event in new_events:
                await events_poller._enqueue(event)
            if new_events:
                logger.info("events_detected", count=len(new_events))
        except Exception:
            logger.exception("events_loop_error")
        await asyncio.sleep(15.0)


async def _odds_loop(odds: OddsApiPoller, detector: EventDetector) -> None:
    while True:
        try:
            lines = await odds.poll_once()
            for line in lines:
                await odds._enqueue(line)
                espn_id = f"{line.get('home_team')}:{line.get('away_team')}"
                prob = line.get("home_prob", 0.5)
                detector.set_baseline(espn_id, prob)
            if lines:
                logger.info("odds_captured", count=len(lines))
        except Exception:
            logger.exception("odds_loop_error")
        await asyncio.sleep(300.0)


async def _detector_loop(detector: EventDetector, trade_queue: asyncio.Queue) -> None:
    while True:
        try:
            event = await detector.espn_queue.get()
            result = await detector.process_event(event)
            if result:
                if trade_queue.full():
                    logger.warning("trade_queue_full")
                await trade_queue.put(result)
        except Exception:
            logger.exception("detector_loop_error")


async def _trader_loop(
    trade_queue: asyncio.Queue,
    simulator: PaperTradeSimulator,
    accumulators: Accumulators,
) -> None:
    while True:
        try:
            opportunity = await trade_queue.get()
            trade = simulator.evaluate_opportunity(opportunity)
            if trade:
                logger.info(
                    "paper_trade_opened",
                    trade_id=trade["id"],
                    sport=trade.get("sport"),
                    size=trade["kelly_size_cents"],
                )
        except Exception:
            logger.exception("trader_loop_error")


async def run_supervisor() -> None:
    espn_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_SIZE)
    trade_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_SIZE)

    scoreboard = EspnScoreboardPoller(espn_queue)
    events_poller = EspnEventsPoller(espn_queue)
    odds = OddsApiPoller(espn_queue)
    detector = EventDetector(espn_queue, trade_queue)
    simulator = PaperTradeSimulator(Portfolio())
    accumulators = Accumulators()

    registry.scoreboard = scoreboard
    registry.events = events_poller
    registry.odds = odds
    registry.detector = detector
    registry.simulator = simulator
    registry.accumulators = accumulators

    logger.info("supervisor_starting")

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(_scoreboard_loop(scoreboard, events_poller))
            tg.create_task(_events_loop(events_poller))
            tg.create_task(_odds_loop(odds, detector))
            tg.create_task(_detector_loop(detector, trade_queue))
            tg.create_task(_trader_loop(trade_queue, simulator, accumulators))
    except* Exception as eg:
        for exc in eg.exceptions:
            logger.error("supervisor_task_crashed", error=str(exc))
    finally:
        await scoreboard.close()
        await events_poller.close()
        await odds.close()
        logger.info("supervisor_shutdown")
