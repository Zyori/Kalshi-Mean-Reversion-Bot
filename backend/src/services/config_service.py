from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.config import ConfigParam

logger = get_logger(__name__)


async def get_all_config(db: AsyncSession) -> Sequence[ConfigParam]:
    stmt = select(ConfigParam).order_by(ConfigParam.key)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_config_value(db: AsyncSession, key: str) -> ConfigParam | None:
    stmt = select(ConfigParam).where(ConfigParam.key == key)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_config(db: AsyncSession, key: str, value: str, reason: str = "") -> ConfigParam:
    param = await get_config_value(db, key)
    if param:
        old_value = param.value
        param.value = value
        logger.info("config_updated", key=key, old=old_value, new=value, reason=reason)
    else:
        param = ConfigParam(key=key, value=value, type="string")
        db.add(param)
        logger.info("config_created", key=key, value=value, reason=reason)

    await db.commit()
    await db.refresh(param)
    return param
