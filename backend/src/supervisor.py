import asyncio
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.analysis.accumulators import Accumulators
from src.config import settings
from src.core.logging import get_logger
from src.ingestion.espn_events import EspnEventsPoller
from src.ingestion.espn_scoreboard import (
    EspnScoreboardPoller,
    is_final_status,
    is_live_status,
)
from src.ingestion.kalshi_rest import KalshiRestClient
from src.ingestion.odds import OddsApiPoller
from src.paper_trader.portfolio import Portfolio
from src.paper_trader.simulator import PaperTradeSimulator
from src.services.decision_service import record_trade_decision
from src.services.ingestion_service import (
    record_game_event,
    record_opening_line,
    upsert_game_from_scoreboard,
)
from src.services.kalshi_market_service import attach_real_market_context
from src.services.paper_runtime import (
    attach_synthetic_market_contexts,
    get_game_by_espn_id,
    persist_trade,
    resolve_game_trades,
    restore_portfolio_state,
)
from src.services.trade_policy_service import evaluate_trade_gate
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
    session_factory: async_sessionmaker,
) -> None:
    while True:
        try:
            updates = await scoreboard.poll_once()
            if updates:
                async with session_factory() as db:
                    for update in updates:
                        await upsert_game_from_scoreboard(db, update)
                        await scoreboard._enqueue(update)
                        espn_id = update.get("espn_id")
                        sport = update.get("sport")
                        status = update.get("status", "")
                        if espn_id and sport and is_live_status(status):
                            events_poller.watch_game(espn_id, sport)
                        elif espn_id and is_final_status(status):
                            events_poller.unwatch_game(espn_id)
                            game = await get_game_by_espn_id(db, espn_id)
                            if game and registry.simulator:
                                await resolve_game_trades(db, registry.simulator, game)
                    await db.commit()
            if updates:
                logger.info("scoreboard_updates", count=len(updates))
        except Exception:
            logger.exception("scoreboard_loop_error")
        await asyncio.sleep(scoreboard.next_interval())


async def _events_loop(
    events_poller: EspnEventsPoller,
    detector: EventDetector,
    trade_queue: asyncio.Queue,
    kalshi_rest: KalshiRestClient,
    session_factory: async_sessionmaker,
) -> None:
    while True:
        try:
            new_events = await events_poller.poll_all()
            if new_events:
                async with session_factory() as db:
                    for event in new_events:
                        game = await get_game_by_espn_id(db, event["espn_id"])
                        if not game:
                            continue
                        event["home_team"] = game.home_team
                        event["away_team"] = game.away_team
                        event["game_status"] = game.status
                        market_payloads: list[dict[str, Any]] = []
                        real_moneyline = await attach_real_market_context(
                            db,
                            kalshi_rest,
                            game,
                            dict(event),
                        )
                        if real_moneyline is not None:
                            market_payloads.append(real_moneyline)

                        synthetic_payloads = await attach_synthetic_market_contexts(
                            db,
                            game,
                            event,
                            include_moneyline=real_moneyline is None,
                        )
                        market_payloads.extend(synthetic_payloads)

                        for enriched in market_payloads:
                            detected = await detector.process_event(enriched)
                            payload = detected or enriched
                            game_event = await record_game_event(db, payload)
                            await events_poller._enqueue(payload)
                            if detected:
                                detected["game_event_id"] = game_event.id if game_event else None
                                if trade_queue.full():
                                    logger.warning("trade_queue_full")
                                await trade_queue.put(detected)
                    await db.commit()
            if new_events:
                logger.info("events_detected", count=len(new_events))
        except Exception:
            logger.exception("events_loop_error")
        await asyncio.sleep(settings.events_poll_interval_s)


async def _odds_loop(
    odds: OddsApiPoller,
    detector: EventDetector,
    session_factory: async_sessionmaker,
) -> None:
    while True:
        try:
            lines = await odds.poll_once()
            if lines:
                async with session_factory() as db:
                    for line in lines:
                        game = await record_opening_line(db, line)
                        await odds._enqueue(line)
                        if game.espn_id:
                            detector.set_baseline(game.espn_id, line.get("home_prob", 0.5))
                    await db.commit()
            if lines:
                logger.info("odds_captured", count=len(lines))
        except Exception:
            logger.exception("odds_loop_error")
        await asyncio.sleep(settings.odds_poll_interval_s)


async def _trader_loop(
    trade_queue: asyncio.Queue,
    simulator: PaperTradeSimulator,
    accumulators: Accumulators,
    session_factory: async_sessionmaker,
) -> None:
    while True:
        try:
            opportunity = await trade_queue.get()
            async with session_factory() as db:
                trade = simulator.evaluate_opportunity(opportunity)
                if trade:
                    skip_reason = await evaluate_trade_gate(db, opportunity, trade)
                    if skip_reason:
                        await record_trade_decision(
                            db,
                            event=opportunity,
                            trade=trade,
                            action="skipped",
                            skip_reason=skip_reason,
                            summary=trade.get("reasoning"),
                        )
                        await db.commit()
                        logger.info(
                            "paper_trade_skipped",
                            market_id=opportunity.get("market_id"),
                            game_event_id=opportunity.get("game_event_id"),
                            reason=skip_reason,
                        )
                        continue

                    record = await persist_trade(
                        db,
                        trade,
                        game_event_id=trade.get("game_event_id"),
                    )
                    await record_trade_decision(
                        db,
                        event=opportunity,
                        trade=trade,
                        action="opened",
                        summary=trade.get("reasoning"),
                    )
                    await db.commit()
                    simulator.activate_trade(record.id, trade)
                    logger.info(
                        "paper_trade_opened",
                        trade_id=record.id,
                        sport=trade.get("sport"),
                        market_category=trade.get("market_category"),
                        side=trade.get("side"),
                        size=trade["kelly_size_cents"],
                    )
                else:
                    await record_trade_decision(
                        db,
                        event=opportunity,
                        trade=None,
                        action="skipped",
                        skip_reason="simulator_rejected",
                    )
                    await db.commit()
                    logger.info(
                        "paper_trade_skipped",
                        market_id=opportunity.get("market_id"),
                        game_event_id=opportunity.get("game_event_id"),
                        reason="simulator_rejected",
                    )
        except Exception:
            logger.exception("trader_loop_error")


async def run_supervisor(session_factory: async_sessionmaker) -> None:
    espn_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_SIZE)
    trade_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_SIZE)

    scoreboard = EspnScoreboardPoller(espn_queue)
    events_poller = EspnEventsPoller(espn_queue)
    odds = OddsApiPoller(espn_queue)
    kalshi_rest = KalshiRestClient()
    detector = EventDetector(espn_queue, trade_queue)
    portfolio = Portfolio()
    async with session_factory() as db:
        await restore_portfolio_state(db, portfolio)
    simulator = PaperTradeSimulator(portfolio)
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
            tg.create_task(_scoreboard_loop(scoreboard, events_poller, session_factory))
            tg.create_task(
                _events_loop(events_poller, detector, trade_queue, kalshi_rest, session_factory)
            )
            tg.create_task(_odds_loop(odds, detector, session_factory))
            tg.create_task(_trader_loop(trade_queue, simulator, accumulators, session_factory))
    except* Exception as eg:
        for exc in eg.exceptions:
            logger.error("supervisor_task_crashed", error=str(exc))
    finally:
        await scoreboard.close()
        await events_poller.close()
        await odds.close()
        await kalshi_rest.close()
        logger.info("supervisor_shutdown")
