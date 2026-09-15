"""Configuração da engine assíncrona SQLAlchemy e gerenciamento de sessões."""

import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from lumi.core.config import Settings, get_settings


def create_app_engine(settings: Settings | None = None) -> AsyncEngine:
    """Cria a instância do AsyncEngine configurada conforme os settings da aplicação."""
    current_settings = settings or get_settings()
    url = current_settings.database_url

    if "sqlite" in url:
        return create_async_engine(url)

    return create_async_engine(
        url,
        pool_size=current_settings.db_pool_size,
        max_overflow=current_settings.db_max_overflow,
        pool_timeout=current_settings.db_pool_timeout,
        echo=current_settings.debug,
    )


# Engine singleton padrão da aplicação
engine: AsyncEngine = create_app_engine()

# Fábrica assíncrona de sessões do banco de dados
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def get_engine() -> AsyncEngine:
    """Retorna o engine assíncrono singleton do SQLAlchemy."""
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retorna a fábrica singleton de sessões assíncronas."""
    return async_session_factory


@asynccontextmanager
async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Context manager assíncrono para operações de banco com commit e rollback determinísticos.

    Em caso de execução bem-sucedida, realiza commit automático.
    Se uma exceção for levantada, executa rollback e propaga o erro.
    A sessão é sempre encerrada ao sair do contexto.
    """
    factory = session_factory or async_session_factory
    session: AsyncSession = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Gerador assíncrono para injeção de dependência no FastAPI via Depends(get_db)."""
    async with get_db_session() as session:
        yield session


# Alias injetável para injeção de AsyncSession em rotas
get_async_session = get_db


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
