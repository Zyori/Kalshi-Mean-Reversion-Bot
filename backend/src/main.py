from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.core.database import create_engine, create_session_factory
from src.core.logging import get_logger, setup_logging

setup_logging(settings.log_level)
logger = get_logger(__name__)

engine = create_engine(settings.database_url)
session_factory = create_session_factory(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting", environment=settings.kalshi_environment.value)
    # Collector tasks will be added in later build steps
    yield
    await engine.dispose()
    logger.info("shutdown_complete")


app = FastAPI(title="Kalshi Mean Reversion Bot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.api.routes.analysis import router as analysis_router  # noqa: E402
from src.api.routes.config import router as config_router  # noqa: E402
from src.api.routes.events import router as events_router  # noqa: E402
from src.api.routes.games import router as games_router  # noqa: E402
from src.api.routes.health import router as health_router  # noqa: E402
from src.api.routes.trades import router as trades_router  # noqa: E402

app.include_router(health_router)
app.include_router(games_router)
app.include_router(events_router)
app.include_router(trades_router)
app.include_router(analysis_router)
app.include_router(config_router)
