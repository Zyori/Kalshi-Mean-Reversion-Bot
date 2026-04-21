import json
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


def serialize_game(game: Game) -> dict[str, Any]:
    return {
        "id": game.id,
        "sport": game.sport,
        "home_team": game.home_team,
        "away_team": game.away_team,
        "start_time": game.start_time.isoformat(),
        "espn_id": game.espn_id,
        "status": game.status,
        "opening_line_home_prob": game.opening_line_home_prob,
        "opening_line_source": game.opening_line_source,
        "latest_home_score": game.latest_home_score,
        "latest_away_score": game.latest_away_score,
        "final_home_score": game.final_home_score,
        "final_away_score": game.final_away_score,
        "created_at": game.created_at.isoformat() if game.created_at else None,
    }


def serialize_event(event: GameEvent) -> dict[str, Any]:
    game = event.game
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
        "detected_at": event.detected_at.isoformat() if event.detected_at else None,
        "estimated_real_at": (
            event.estimated_real_at.isoformat() if event.estimated_real_at else None
        ),
        "classification": event.classification,
        "confidence_score": event.confidence_score,
        "kalshi_price_at": event.kalshi_price_at,
        "baseline_prob": event.baseline_prob,
        "deviation": event.deviation,
        "espn_data": _loads_json(event.espn_data),
    }


def serialize_trade(trade: PaperTrade) -> dict[str, Any]:
    trigger_event = trade.game_event
    trigger_game = trigger_event.game if trigger_event else None
    matchup = (
        f"{trigger_game.away_team} @ {trigger_game.home_team}" if trigger_game else None
    )
    selected_team = None
    opposing_team = None
    if trigger_game:
        if trade.side == "yes":
            selected_team = trigger_game.home_team
            opposing_team = trigger_game.away_team
        elif trade.side == "no":
            selected_team = trigger_game.away_team
            opposing_team = trigger_game.home_team
    return {
        "id": trade.id,
        "game_event_id": trade.game_event_id,
        "market_id": trade.market_id,
        "sport": trade.sport,
        "side": trade.side,
        "matchup": matchup,
        "selected_team": selected_team,
        "opposing_team": opposing_team,
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
        "entered_at": trade.entered_at.isoformat() if trade.entered_at else None,
        "resolved_at": trade.resolved_at.isoformat() if trade.resolved_at else None,
        "resolution": trade.resolution,
        "game_context": _loads_json(trade.game_context),
        "reasoning": trade.reasoning,
        "skip_reason": trade.skip_reason,
        "trigger_event": serialize_event(trigger_event) if trigger_event else None,
        "game": serialize_game(trigger_game) if trigger_game else None,
    }
