"""Fixtures globais de teste utilizando pytest e httpx."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from lumi.main import app


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Fixture de cliente HTTP assíncrono para testar endpoints FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
