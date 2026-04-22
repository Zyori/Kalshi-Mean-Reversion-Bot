import json
from datetime import UTC, datetime
from typing import Any

from src.models.game import Game, GameEvent
from src.models.trade import PaperTrade


def _loads_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return value.isoformat()


def serialize_game(game: Game) -> dict[str, Any]:
    return {
        "id": game.id,
        "sport": game.sport,
        "home_team": game.home_team,
        "away_team": game.away_team,
        "start_time": _serialize_datetime(game.start_time),
        "espn_id": game.espn_id,
        "status": game.status,
        "opening_line_home_prob": game.opening_line_home_prob,
        "opening_line_source": game.opening_line_source,
        "opening_spread_home": game.opening_spread_home,
        "opening_spread_away": game.opening_spread_away,
        "opening_total": game.opening_total,
        "opening_home_team_total": game.opening_home_team_total,
        "opening_away_team_total": game.opening_away_team_total,
        "latest_home_score": game.latest_home_score,
        "latest_away_score": game.latest_away_score,
        "final_home_score": game.final_home_score,
        "final_away_score": game.final_away_score,
        "created_at": _serialize_datetime(game.created_at),
    }


def serialize_event(event: GameEvent) -> dict[str, Any]:
    game = event.game
    espn_data = _loads_json(event.espn_data)
    market_category = espn_data.get("market_category") if isinstance(espn_data, dict) else None
    market_source = espn_data.get("market_source") if isinstance(espn_data, dict) else None
    market_label_yes = espn_data.get("market_label_yes") if isinstance(espn_data, dict) else None
    market_label_no = espn_data.get("market_label_no") if isinstance(espn_data, dict) else None
    return {
        "id": event.id,
        "game_id": event.game_id,
        "sport": game.sport if game else None,
        "home_team": game.home_team if game else None,
        "away_team": game.away_team if game else None,
        "game_status": game.status if game else None,
        "event_type": event.event_type,
        "description": event.description,
        "home_score": event.home_score,
        "away_score": event.away_score,
        "period": event.period,
        "clock": event.clock,
        "detected_at": _serialize_datetime(event.detected_at),
        "estimated_real_at": _serialize_datetime(event.estimated_real_at),
        "classification": event.classification,
        "confidence_score": event.confidence_score,
        "kalshi_price_at": event.kalshi_price_at,
        "baseline_prob": event.baseline_prob,
        "deviation": event.deviation,
        "market_category": market_category,
        "market_source": market_source,
        "market_label_yes": market_label_yes,
        "market_label_no": market_label_no,
        "espn_data": espn_data,
    }


def serialize_trade(trade: PaperTrade) -> dict[str, Any]:
    trigger_event = trade.game_event
    trigger_game = trigger_event.game if trigger_event else None
    game_context = _loads_json(trade.game_context)
    matchup = (
        f"{trigger_game.away_team} @ {trigger_game.home_team}" if trigger_game else None
    )
    selected_team = None
    opposing_team = None
    contract_label_yes = None
    contract_label_no = None
    if isinstance(game_context, dict):
        contract_label_yes = game_context.get("market_label_yes")
        contract_label_no = game_context.get("market_label_no")
        if trade.side == "yes":
            selected_team = contract_label_yes
            opposing_team = contract_label_no
        elif trade.side == "no":
            selected_team = contract_label_no
            opposing_team = contract_label_yes
    if selected_team is None and trigger_game:
        if trade.side == "yes":
            selected_team = trigger_game.home_team
            opposing_team = trigger_game.away_team
        elif trade.side == "no":
            selected_team = trigger_game.away_team
            opposing_team = trigger_game.home_team
    if contract_label_yes is None and trigger_game:
        contract_label_yes = trigger_game.home_team
        contract_label_no = trigger_game.away_team
    return {
        "id": trade.id,
        "game_event_id": trade.game_event_id,
        "market_id": trade.market_id,
        "sport": trade.sport,
        "market_category": trade.market_category,
        "side": trade.side,
        "matchup": matchup,
        "selected_team": selected_team,
        "opposing_team": opposing_team,
        "contract_label_yes": contract_label_yes,
        "contract_label_no": contract_label_no,
        "entry_price": trade.entry_price,
        "entry_price_adj": trade.entry_price_adj,
        "slippage_cents": trade.slippage_cents,
        "confidence_score": trade.confidence_score,
        "kelly_fraction": trade.kelly_fraction,
        "kelly_size_cents": trade.kelly_size_cents,
        "flat_size_cents": getattr(trade, "flat_size_cents", None),
        "exit_price": trade.exit_price,
        "pnl_cents": trade.pnl_cents,
        "pnl_kelly_cents": trade.pnl_kelly_cents,
        "status": trade.status,
        "entered_at": _serialize_datetime(trade.entered_at),
        "resolved_at": _serialize_datetime(trade.resolved_at),
        "resolution": trade.resolution,
        "game_context": game_context,
        "reasoning": trade.reasoning,
        "skip_reason": trade.skip_reason,
        "trigger_event": serialize_event(trigger_event) if trigger_event else None,
        "game": serialize_game(trigger_game) if trigger_game else None,
    }
