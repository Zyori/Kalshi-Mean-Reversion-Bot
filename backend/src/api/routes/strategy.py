from fastapi import APIRouter

from src.strategy.catalog import get_strategy_catalog

router = APIRouter(prefix="/api")


@router.get("/strategy")
async def strategy_catalog():
    return get_strategy_catalog()
