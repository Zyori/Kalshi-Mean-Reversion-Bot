import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.config import settings
from src.models.analysis import Insight
from src.models.trade import PaperTrade

router = APIRouter(prefix="/api")


def _load_trade_context(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


@router.get("/analysis/summary")
async def analysis_summary(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(PaperTrade.id)))
    wins = await db.scalar(
        select(func.count(PaperTrade.id)).where(PaperTrade.status == "resolved_win")
    )
    losses = await db.scalar(
        select(func.count(PaperTrade.id)).where(PaperTrade.status == "resolved_loss")
    )
    total_pnl = await db.scalar(select(func.sum(PaperTrade.pnl_cents))) or 0
    pending_wagers = await db.scalar(
        select(func.sum(PaperTrade.kelly_size_cents)).where(PaperTrade.status == "open")
    ) or 0
    open_count = await db.scalar(
        select(func.count(PaperTrade.id)).where(PaperTrade.status == "open")
    )

    resolved = (wins or 0) + (losses or 0)
    win_rate = (wins or 0) / resolved if resolved > 0 else 0.0
    starting_bankroll = settings.paper_bankroll_start_cents
    current_bankroll = starting_bankroll + total_pnl
    available_bankroll = current_bankroll - pending_wagers

    return {
        "total_trades": total or 0,
        "open": open_count or 0,
        "resolved": resolved,
        "wins": wins or 0,
        "losses": losses or 0,
        "win_rate": round(win_rate, 4),
        "total_pnl_cents": total_pnl,
        "starting_bankroll_cents": starting_bankroll,
        "current_bankroll_cents": current_bankroll,
        "available_bankroll_cents": available_bankroll,
        "pending_wagers_cents": pending_wagers,
    }


@router.get("/analysis/by-sport")
async def analysis_by_sport(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            PaperTrade.sport,
            func.count(PaperTrade.id).label("count"),
            func.sum(PaperTrade.pnl_cents).label("total_pnl"),
        )
        .where(PaperTrade.status.in_(["resolved_win", "resolved_loss"]))
        .group_by(PaperTrade.sport)
    )
    result = await db.execute(stmt)
    return [
        {"sport": row.sport, "count": row.count, "total_pnl_cents": row.total_pnl or 0}
        for row in result
    ]


@router.get("/analysis/by-event-type")
async def analysis_by_event_type(db: AsyncSession = Depends(get_db)):
    stmt = select(PaperTrade.game_context, PaperTrade.pnl_cents).where(
        PaperTrade.status.in_(["resolved_win", "resolved_loss", "resolved_push"])
    )
    result = await db.execute(stmt)
    buckets: dict[str, dict[str, int]] = {}
    for row in result:
        context = _load_trade_context(row.game_context)
        event_type = context.get("event_type") or "unknown"
        bucket = buckets.setdefault(event_type, {"count": 0, "total_pnl_cents": 0})
        bucket["count"] += 1
        bucket["total_pnl_cents"] += row.pnl_cents or 0

    items = [
        {"event_type": event_type, **stats}
        for event_type, stats in buckets.items()
    ]
    items.sort(key=lambda item: (-item["count"], item["event_type"]))
    return items[:20]


@router.get("/analysis/by-market-category")
async def analysis_by_market_category(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            PaperTrade.market_category,
            func.count(PaperTrade.id).label("count"),
            func.sum(PaperTrade.pnl_cents).label("total_pnl"),
        )
        .where(PaperTrade.status.in_(["resolved_win", "resolved_loss", "resolved_push"]))
        .group_by(PaperTrade.market_category)
    )
    result = await db.execute(stmt)
    return [
        {
            "market_category": row.market_category,
            "count": row.count,
            "total_pnl_cents": row.total_pnl or 0,
        }
        for row in result
    ]


@router.get("/analysis/equity-curve")
async def equity_curve(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(PaperTrade.resolved_at, PaperTrade.pnl_cents)
        .where(PaperTrade.resolved_at.isnot(None))
        .order_by(PaperTrade.resolved_at)
    )
    result = await db.execute(stmt)
    cumulative = 0
    points = []
    for row in result:
        cumulative += row.pnl_cents or 0
        points.append(
            {"time": row.resolved_at.isoformat() if row.resolved_at else None, "pnl": cumulative}
        )
    return points


@router.get("/analysis/kelly-comparison")
async def kelly_comparison(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(PaperTrade.pnl_cents, PaperTrade.pnl_kelly_cents)
        .where(PaperTrade.status.in_(["resolved_win", "resolved_loss"]))
        .order_by(PaperTrade.resolved_at)
    )
    result = await db.execute(stmt)
    kelly_cum = 0
    flat_cum = 0
    points = []
    for row in result:
        kelly_cum += row.pnl_kelly_cents or 0
        flat_cum += row.pnl_cents or 0
        points.append({"kelly": kelly_cum, "flat": flat_cum})
    return points


@router.get("/insights")
async def list_insights(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Insight).order_by(Insight.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Insight.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()
