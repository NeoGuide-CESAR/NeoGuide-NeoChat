"""Configuração da engine assíncrona SQLAlchemy e gerenciamento de sessões."""

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
