from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.serializers import serialize_trade
from src.services.trade_service import get_active_trades, get_trade_by_id, get_trades

router = APIRouter(prefix="/api")


@router.get("/trades")
async def list_trades(
    sport: str | None = None,
    status: str | None = None,
    sort_by: str = "entered_at",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    trades = await get_trades(
        db,
        sport=sport,
        status=status,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return [serialize_trade(trade) for trade in trades]


@router.get("/trades/active")
async def active_trades(db: AsyncSession = Depends(get_db)):
    trades = await get_active_trades(db)
    return [serialize_trade(trade) for trade in trades]


@router.get("/trades/{trade_id}")
async def get_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    trade = await get_trade_by_id(db, trade_id)
    if not trade:
        return {"error": "Trade not found"}, 404
    return serialize_trade(trade)
