"""Contract tests for the SportConfigRegistry — the single source of truth
for per-sport engagement modes."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database import Base, create_engine
from src.core.types import Sport, SportMode
from src.models import SportConfig
from src.services.sport_config import SportConfigRegistry


@pytest.fixture
async def session_factory():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed(db: AsyncSession, modes: dict[Sport, SportMode]) -> None:
    for sport, mode in modes.items():
        db.add(SportConfig(sport=sport, mode=mode))
    await db.commit()


async def test_load_returns_registry_with_seeded_modes(session_factory):
    async with session_factory() as db:
        await _seed(db, {Sport.SOCCER: SportMode.ACTIVE, Sport.NFL: SportMode.PASSIVE})
        registry = await SportConfigRegistry.load(db)

    assert registry.is_active(Sport.SOCCER)
    assert registry.is_passive(Sport.NFL)


async def test_missing_sport_defaults_to_off(session_factory):
    async with session_factory() as db:
        await _seed(db, {Sport.SOCCER: SportMode.ACTIVE})
        registry = await SportConfigRegistry.load(db)

    # Unseeded sports must default to OFF, never silently active.
    assert registry.mode(Sport.NBA) == SportMode.OFF
    assert not registry.is_active(Sport.NBA)
    assert not registry.is_passive(Sport.NBA)


async def test_polled_sports_excludes_off(session_factory):
    async with session_factory() as db:
        await _seed(
            db,
            {
                Sport.SOCCER: SportMode.ACTIVE,
                Sport.UFC: SportMode.PASSIVE,
                Sport.NHL: SportMode.OFF,
            },
        )
        registry = await SportConfigRegistry.load(db)

    polled = set(registry.polled_sports())
    assert Sport.SOCCER in polled
    assert Sport.UFC in polled
    assert Sport.NHL not in polled


async def test_active_sports_returns_only_active(session_factory):
    async with session_factory() as db:
        await _seed(
            db,
            {Sport.SOCCER: SportMode.ACTIVE, Sport.UFC: SportMode.PASSIVE},
        )
        registry = await SportConfigRegistry.load(db)

    assert registry.active_sports() == [Sport.SOCCER]


async def test_reload_refreshes_modes(session_factory):
    async with session_factory() as db:
        await _seed(db, {Sport.SOCCER: SportMode.PASSIVE})
        registry = await SportConfigRegistry.load(db)
        assert registry.is_passive(Sport.SOCCER)

        existing = await db.get(SportConfig, Sport.SOCCER)
        existing.mode = SportMode.ACTIVE
        await db.commit()

        await registry.reload(db)
        assert registry.is_active(Sport.SOCCER)


async def test_accepts_string_sport_keys(session_factory):
    async with session_factory() as db:
        await _seed(db, {Sport.SOCCER: SportMode.ACTIVE})
        registry = await SportConfigRegistry.load(db)

    assert registry.is_active("soccer")
    assert registry.mode("nba") == SportMode.OFF
