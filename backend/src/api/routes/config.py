from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.services.config_service import get_all_config, update_config

router = APIRouter(prefix="/api")


class ConfigUpdate(BaseModel):
    value: str
    reason: str = ""


@router.get("/config")
async def list_config(db: AsyncSession = Depends(get_db)):
    return await get_all_config(db)


@router.patch("/config/{key}")
async def patch_config(key: str, body: ConfigUpdate, db: AsyncSession = Depends(get_db)):
    param = await update_config(db, key, body.value, body.reason)
    return param
