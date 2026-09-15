"""Gerenciamento de conexões assíncronas e sessões SQLAlchemy para o Lumi."""

import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from lumi.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Retorna ou inicializa o engine assíncrono singleton do SQLAlchemy."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            echo=False,
            future=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retorna ou inicializa a fábrica de sessões assíncronas."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager assíncrono para obtenção e liberação segura de uma AsyncSession."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependência FastAPI injetável para injeção de AsyncSession em rotas."""
    async with get_db_session() as session:
        yield session


def sanitize_db_error(error: Exception | str) -> str:
    """Sanitiza mensagens de erro de banco de dados removendo credenciais e senhas."""
    message = str(error)
    # Remove senhas em URIs de conexão como postgresql+asyncpg://user:password@host:port/db
    sanitized = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", message)
    # Remove menções diretas de senhas
    sanitized = re.sub(
        r"password=['\"][^'\"]+['\"]", "password='***'", sanitized, flags=re.IGNORECASE
    )
    sanitized = re.sub(r"password\s*=\s*[^\s]+", "password=***", sanitized, flags=re.IGNORECASE)
    return sanitized
