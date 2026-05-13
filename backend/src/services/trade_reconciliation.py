"""Trade reconciliation — close out paper trades for games that have ended.

Two failure modes this guards against:

1. The scoreboard loop only triggers resolution on the *transition* into
   a final status. If a game went final while the supervisor was down,
   the trigger was missed and the trades stay open forever.
2. Older ingestion code only recognised a few US-sports final tokens, so
   soccer games ending FULL_TIME had `final_home_score` left NULL even
   though `latest_home_score` had the correct value.

`reconcile_open_trades` finds open trades whose linked game is in a
final status, repairs the final score from latest_* when needed, and
runs the normal resolve_game_trades path to close them out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.core.logging import get_logger
from src.ingestion.espn_scoreboard import is_final_status
from src.models.game import Game
from src.models.market import Market
from src.models.trade import PaperTrade
from src.services.paper_runtime import resolve_game_trades

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.paper_trader.simulator import PaperTradeSimulator

logger = get_logger(__name__)


async def reconcile_open_trades(
    db: AsyncSession,
    simulator: PaperTradeSimulator,
) -> int:
    """Close out any open trades whose game has finished. Returns the
    number of trades resolved so callers can log progress."""
    result = await db.execute(
        select(Game)
        .join(Market, Market.game_id == Game.id)
        .join(PaperTrade, PaperTrade.market_id == Market.id)
        .where(PaperTrade.status == "open")
        .distinct()
    )
    games = result.scalars().all()
    resolved_count = 0
    for game in games:
        if not is_final_status(game.status):
            continue
        # Backfill the final score from the last live score when needed.
        # Soccer games that ended FULL_TIME before the ingestion fix
        # landed have final_*_score = NULL but a correct latest_*_score.
        if game.final_home_score is None and game.latest_home_score is not None:
            game.final_home_score = game.latest_home_score
        if game.final_away_score is None and game.latest_away_score is not None:
            game.final_away_score = game.latest_away_score
        resolved = await resolve_game_trades(db, simulator, game)
        resolved_count += len(resolved)
    if resolved_count:
        await db.commit()
        logger.info("reconciliation_complete", trades_resolved=resolved_count)
    return resolved_count
