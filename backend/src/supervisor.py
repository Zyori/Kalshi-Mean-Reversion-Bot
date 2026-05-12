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
from src.services.heartbeat import HeartbeatRegistry, LoopHeartbeat
from src.services.ingestion_service import (
    record_game_event,
    record_opening_line,
    upsert_game_from_scoreboard,
)
from src.services.kalshi_market_service import (
    active_markets_for_sports,
    attach_real_market_context,
    capture_market_snapshot,
)
from src.services.paper_runtime import (
    attach_synthetic_market_contexts,
    get_game_by_espn_id,
    persist_trade,
    resolve_game_trades,
    restore_portfolio_state,
)
from src.services.sport_config import SportConfigRegistry
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
    sport_config: SportConfigRegistry = field(default_factory=SportConfigRegistry)
    heartbeats: HeartbeatRegistry = field(default_factory=HeartbeatRegistry)

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
    hb: LoopHeartbeat,
) -> None:
    while True:
        hb.tick()
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
                        # Only active sports get live event-by-event polling
                        # and paper trades. Passive sports stop at scheduling.
                        if (
                            espn_id
                            and sport
                            and is_live_status(status)
                            and registry.sport_config.is_active(sport)
                        ):
                            events_poller.watch_game(espn_id, sport)
                        elif espn_id and is_final_status(status):
                            events_poller.unwatch_game(espn_id)
                            game = await get_game_by_espn_id(db, espn_id)
                            if game and registry.simulator:
                                await resolve_game_trades(db, registry.simulator, game)
                    await db.commit()
            if updates:
                logger.info("scoreboard_updates", count=len(updates))
            hb.success()
        except Exception as e:
            hb.error(e)
            logger.exception("scoreboard_loop_error")
        await asyncio.sleep(scoreboard.next_interval())


async def _events_loop(
    events_poller: EspnEventsPoller,
    detector: EventDetector,
    trade_queue: asyncio.Queue,
    kalshi_rest: KalshiRestClient,
    session_factory: async_sessionmaker,
    hb: LoopHeartbeat,
) -> None:
    while True:
        hb.tick()
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
            hb.success()
        except Exception as e:
            hb.error(e)
            logger.exception("events_loop_error")
        await asyncio.sleep(settings.events_poll_interval_s)


async def _snapshot_loop(
    kalshi_rest: KalshiRestClient,
    session_factory: async_sessionmaker,
    hb: LoopHeartbeat,
) -> None:
    """Periodic Kalshi orderbook snapshots for active-sport markets.

    Builds the price time series we'd otherwise miss when no in-game event
    fires (e.g. a quiet 30-min stretch). Event-driven snapshots (via
    `attach_real_market_context`) remain authoritative for the trader; this
    loop is purely for research/analytics density.
    """
    while True:
        hb.tick()
        try:
            active_sports = [s.value for s in registry.sport_config.active_sports()]
            if active_sports:
                async with session_factory() as db:
                    markets = await active_markets_for_sports(db, active_sports)
                    for market in markets:
                        try:
                            await capture_market_snapshot(db, kalshi_rest, market)
                        except Exception:
                            logger.exception(
                                "snapshot_capture_failed",
                                market_id=market.id,
                                ticker=market.kalshi_ticker,
                            )
                    await db.commit()
                    if markets:
                        logger.info("snapshots_captured", count=len(markets))
            hb.success()
        except Exception as e:
            hb.error(e)
            logger.exception("snapshot_loop_error")
        await asyncio.sleep(settings.kalshi_snapshot_poll_interval_s)


async def _odds_loop(
    odds: OddsApiPoller,
    detector: EventDetector,
    session_factory: async_sessionmaker,
    hb: LoopHeartbeat,
) -> None:
    while True:
        hb.tick()
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
            hb.success()
        except Exception as e:
            hb.error(e)
            logger.exception("odds_loop_error")
        await asyncio.sleep(settings.odds_poll_interval_s)


async def _trader_loop(
    trade_queue: asyncio.Queue,
    simulator: PaperTradeSimulator,
    accumulators: Accumulators,
    session_factory: async_sessionmaker,
    hb: LoopHeartbeat,
) -> None:
    # Tick this often even when the queue is idle so the watchdog can tell
    # the difference between "no trade opportunities lately" and "the trader
    # is wedged." Trader is a consumer, so without an idle timeout it would
    # block forever on get() and never re-tick.
    idle_tick_interval_s = settings.events_poll_interval_s
    while True:
        hb.tick()
        try:
            try:
                opportunity = await asyncio.wait_for(
                    trade_queue.get(), timeout=idle_tick_interval_s
                )
            except TimeoutError:
                hb.success()
                continue
            # Defense in depth: even if a passive sport's event reaches us,
            # never open a paper trade for a non-active sport.
            opp_sport = opportunity.get("sport")
            if opp_sport and not registry.sport_config.is_active(opp_sport):
                logger.debug("paper_trade_skipped_inactive_sport", sport=opp_sport)
                hb.success()
                continue
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
                        hb.success()
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
            hb.success()
        except Exception as e:
            hb.error(e)
            logger.exception("trader_loop_error")


async def run_supervisor(session_factory: async_sessionmaker) -> None:
    espn_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_SIZE)
    trade_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_SIZE)

    async with session_factory() as db:
        sport_config = await SportConfigRegistry.load(db)

    polled = [s.value for s in sport_config.polled_sports()]
    scoreboard = EspnScoreboardPoller(espn_queue, sports=polled)
    events_poller = EspnEventsPoller(espn_queue)
    odds = OddsApiPoller(espn_queue, sports=polled)
    kalshi_rest = KalshiRestClient()
    detector = EventDetector(espn_queue, trade_queue)
    portfolio = Portfolio()
    async with session_factory() as db:
        await restore_portfolio_state(db, portfolio)
    simulator = PaperTradeSimulator(portfolio)
    accumulators = Accumulators()

    heartbeats = HeartbeatRegistry()
    scoreboard_hb = heartbeats.register(
        "scoreboard", settings.scoreboard_pregame_poll_interval_s
    )
    events_hb = heartbeats.register("events", settings.events_poll_interval_s)
    odds_hb = heartbeats.register("odds", settings.odds_poll_interval_s)
    snapshot_hb = heartbeats.register(
        "snapshot", settings.kalshi_snapshot_poll_interval_s
    )
    # Trader has no fixed interval — it blocks on the queue. Use the events
    # interval as a generous staleness bound; an empty queue is not unhealthy.
    trader_hb = heartbeats.register("trader", settings.events_poll_interval_s * 4)

    registry.scoreboard = scoreboard
    registry.events = events_poller
    registry.odds = odds
    registry.detector = detector
    registry.simulator = simulator
    registry.accumulators = accumulators
    registry.sport_config = sport_config
    registry.heartbeats = heartbeats

    logger.info(
        "supervisor_starting",
        active_sports=[s.value for s in sport_config.active_sports()],
        polled_sports=polled,
    )

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                _scoreboard_loop(scoreboard, events_poller, session_factory, scoreboard_hb)
            )
            tg.create_task(
                _events_loop(
                    events_poller, detector, trade_queue, kalshi_rest, session_factory, events_hb
                )
            )
            tg.create_task(_odds_loop(odds, detector, session_factory, odds_hb))
            tg.create_task(_snapshot_loop(kalshi_rest, session_factory, snapshot_hb))
            tg.create_task(
                _trader_loop(
                    trade_queue, simulator, accumulators, session_factory, trader_hb
                )
            )
    except* Exception as eg:
        for exc in eg.exceptions:
            logger.error("supervisor_task_crashed", error=str(exc))
    finally:
        await scoreboard.close()
        await events_poller.close()
        await odds.close()
        await kalshi_rest.close()
        logger.info("supervisor_shutdown")
