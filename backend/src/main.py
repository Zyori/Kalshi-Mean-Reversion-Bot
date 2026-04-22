import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.core.database import create_engine, create_session_factory
from src.core.logging import get_logger, setup_logging
from src.core.security import require_auth
from src.supervisor import run_supervisor

setup_logging(settings.log_level)
logger = get_logger(__name__)

engine = create_engine(settings.database_url)
session_factory = create_session_factory(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting", environment=settings.kalshi_environment.value)
    supervisor_task = asyncio.create_task(run_supervisor(session_factory))
    yield
    supervisor_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await supervisor_task
    await engine.dispose()
    logger.info("shutdown_complete")


app = FastAPI(
    title="Kalshi Mean Reversion Bot",
    lifespan=lifespan,
    docs_url=None if settings.is_prod else "/docs",
    redoc_url=None if settings.is_prod else "/redoc",
    openapi_url=None if settings.is_prod else "/openapi.json",
)

_cors_origins = (
    ["https://mrb.lutz.bot", "https://lutz.bot"]
    if settings.is_prod
    else ["http://localhost:5173", "https://mrb.lutz.bot", "https://lutz.bot"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.api.routes.analysis import router as analysis_router  # noqa: E402
from src.api.routes.auth import router as auth_router  # noqa: E402
from src.api.routes.config import router as config_router  # noqa: E402
from src.api.routes.events import router as events_router  # noqa: E402
from src.api.routes.games import router as games_router  # noqa: E402
from src.api.routes.health import router as health_router  # noqa: E402
from src.api.routes.public import router as public_router  # noqa: E402
from src.api.routes.strategy import router as strategy_router  # noqa: E402
from src.api.routes.trades import router as trades_router  # noqa: E402

# Unauthenticated
app.include_router(auth_router)
app.include_router(public_router)

# Authenticated — require_auth is applied at the include level
_auth = [Depends(require_auth)]
app.include_router(health_router, dependencies=_auth)
app.include_router(games_router, dependencies=_auth)
app.include_router(events_router, dependencies=_auth)
app.include_router(trades_router, dependencies=_auth)
app.include_router(analysis_router, dependencies=_auth)
app.include_router(config_router, dependencies=_auth)
app.include_router(strategy_router, dependencies=_auth)
