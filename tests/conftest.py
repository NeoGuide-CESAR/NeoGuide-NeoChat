"""Fixtures globais de teste utilizando pytest e httpx."""

import socket
from collections.abc import AsyncGenerator
from urllib.parse import urlparse

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.core.config import get_settings
from lumi.db.session import get_engine
from lumi.main import app


def is_postgres_available() -> bool:
    """Verifica rapidamente se a porta do PostgreSQL está acessível."""
    try:
        settings = get_settings()
        url = urlparse(settings.database_url)
        host = url.hostname or "localhost"
        port = url.port or 5432
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex((host, port)) == 0
    except Exception:
        return False


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Fixture de cliente HTTP assíncrono para testar endpoints FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Headers contendo X-API-Key válida."""
    settings = get_settings()
    return {"X-API-Key": settings.api_key}


@pytest.fixture
def require_database() -> None:
    """Fixture defensiva que pula o teste graciosamente se o banco de dados não estiver ativo."""
    if not is_postgres_available():
        pytest.skip("PostgreSQL/pgvector não disponível no ambiente")


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fixture de banco de dados para testes de integração com transação assíncrona SQLAlchemy e rollback.

    Verifica a disponibilidade do PostgreSQL/pgvector e executa skip gracioso se inacessível.
    """
    if not is_postgres_available():
        pytest.skip("PostgreSQL/pgvector não disponível no ambiente")

    engine = get_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("PostgreSQL/pgvector não disponível no ambiente")

    async with engine.connect() as connection:
        trans = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
