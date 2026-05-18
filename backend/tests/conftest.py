from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.routes import auth
from src.main import app


@pytest.fixture(autouse=True)
def _reset_login_rate_limiter():
    """Clear the login rate-limiter between tests.

    The limiter keeps per-IP attempt counts in a module-level dict. Every
    test hits the ASGI app from the same client IP, so without this reset
    the counts accumulate across the session and later tests get 429ed.
    """
    auth._attempts.clear()
    yield
    auth._attempts.clear()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
