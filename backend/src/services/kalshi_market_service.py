import time
import unicodedata
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.ingestion.kalshi_rest import KalshiRestClient
from src.models.game import Game
from src.models.market import Market, MarketSnapshot

logger = get_logger(__name__)

MATCH_FAILURE_COOLDOWN_S = 1800
REAL_MARKET_TYPE = "kalshi_game_winner_demo"
_failed_match_cache: dict[int, float] = {}


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().replace("&", "and")
    for token in (".", ",", "?", "'", '"', "fc", "cf"):
        normalized = normalized.replace(token, " ")
    return " ".join(normalized.split())


def _team_aliases(team: str) -> set[str]:
    normalized = _normalize_text(team)
    tokens = [token for token in normalized.split() if len(token) > 2]
    aliases = {normalized}
    if tokens:
        aliases.add(tokens[0])
        aliases.add(tokens[-1])
    if len(tokens) >= 2:
        aliases.add(" ".join(tokens[:2]))
    return {alias for alias in aliases if alias}


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _within_match_window(game: Game, market_row: dict[str, Any]) -> bool:
    expected = _parse_datetime(market_row.get("expected_expiration_time"))
    if expected is None:
        expected = _parse_datetime(market_row.get("expiration_time"))
    if expected is None:
        return False

    game_start = game.start_time if game.start_time.tzinfo else game.start_time.replace(tzinfo=UTC)
    return abs((expected - game_start).total_seconds()) <= 36 * 3600


def _title_matches_game(game: Game, market_row: dict[str, Any]) -> bool:
    title = _normalize_text(market_row.get("event_title") or market_row.get("market_title") or "")
    home_aliases = _team_aliases(game.home_team)
    away_aliases = _team_aliases(game.away_team)
    home_match = any(alias in title for alias in home_aliases)
    away_match = any(alias in title for alias in away_aliases)
    return home_match and away_match


def _yes_side_matches_home(game: Game, market_row: dict[str, Any]) -> bool:
    yes_label = _normalize_text(market_row.get("yes_sub_title") or "")
    return any(alias in yes_label for alias in _team_aliases(game.home_team))


async def _existing_real_market(db: AsyncSession, game_id: int) -> Market | None:
    result = await db.execute(
        select(Market).where(Market.game_id == game_id, Market.market_type == REAL_MARKET_TYPE)
    )
    return result.scalar_one_or_none()


async def ensure_real_kalshi_market(
    db: AsyncSession,
    rest: KalshiRestClient,
    game: Game,
) -> Market | None:
    existing = await _existing_real_market(db, game.id)
    if existing is not None:
        return existing

    failed_at = _failed_match_cache.get(game.id)
    if failed_at is not None and (time.time() - failed_at) < MATCH_FAILURE_COOLDOWN_S:
        return None

    try:
        candidates = await rest.get_active_game_markets(game.sport)
    except Exception:
        logger.exception("kalshi_market_discovery_failed", game_id=game.id, sport=game.sport)
        _failed_match_cache[game.id] = time.time()
        return None

    for candidate in candidates:
        if not _within_match_window(game, candidate):
            continue
        if not _title_matches_game(game, candidate):
            continue
        if not _yes_side_matches_home(game, candidate):
            continue

        market = Market(
            game_id=game.id,
            kalshi_ticker=candidate["market_ticker"],
            market_type=REAL_MARKET_TYPE,
            opened_at=_parse_datetime(candidate.get("expected_expiration_time")),
        )
        db.add(market)
        await db.flush()
        logger.info(
            "kalshi_market_matched",
            game_id=game.id,
            ticker=market.kalshi_ticker,
            event_ticker=candidate.get("event_ticker"),
        )
        return market

    _failed_match_cache[game.id] = time.time()
    return None


def _best_bid(levels: list[list[str]]) -> int | None:
    if not levels:
        return None
    return max(round(float(price) * 100) for price, _quantity in levels)


def _depth(levels: list[list[str]]) -> int | None:
    if not levels:
        return None
    return round(sum(float(quantity) for _price, quantity in levels))


async def attach_real_market_context(
    db: AsyncSession,
    rest: KalshiRestClient,
    game: Game,
    event: dict[str, Any],
) -> dict[str, Any] | None:
    market = await ensure_real_kalshi_market(db, rest, game)
    if market is None:
        return None

    orderbook = await rest.get_orderbook(market.kalshi_ticker, depth=5)
    orderbook_fp = orderbook.get("orderbook_fp") or {}
    yes_levels = orderbook_fp.get("yes_dollars") or []
    no_levels = orderbook_fp.get("no_dollars") or []

    yes_bid = _best_bid(yes_levels)
    no_bid = _best_bid(no_levels)
    yes_ask = 100 - no_bid if no_bid is not None else None
    no_ask = 100 - yes_bid if yes_bid is not None else None
    if yes_ask is None:
        return None
    yes_ask_depth = _depth(no_levels)
    no_ask_depth = _depth(yes_levels)

    snapshot = MarketSnapshot(
        market_id=market.id,
        kalshi_bid=yes_bid,
        kalshi_ask=yes_ask,
        kalshi_volume=None,
        bid_depth=_depth(yes_levels),
        ask_depth=yes_ask_depth,
    )
    db.add(snapshot)
    await db.flush()

    event["market_id"] = market.id
    event["market_type"] = market.market_type
    event["market_category"] = "moneyline"
    event["market_source"] = "kalshi_demo"
    event["market_label_yes"] = game.home_team
    event["market_label_no"] = game.away_team
    event["kalshi_price_at"] = yes_ask
    event["kalshi_yes_bid"] = yes_bid
    event["kalshi_yes_ask"] = yes_ask
    event["kalshi_no_ask"] = no_ask
    event["kalshi_yes_ask_depth"] = yes_ask_depth
    event["kalshi_no_ask_depth"] = no_ask_depth
    event["ask_depth"] = yes_ask_depth
    event["fair_prob_yes"] = game.opening_line_home_prob or 0.5
    return event
