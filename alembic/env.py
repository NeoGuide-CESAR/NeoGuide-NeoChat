"""Configuração de ambiente de migrações assíncronas do Alembic."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from lumi.core.config import get_settings
from lumi.db.models import Base

# Objeto de configuração do Alembic
config = context.config

# Interpreta configuração de logging do alembic.ini se presente
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadados alvo para detecção e autogenerate de migrações
target_metadata = Base.metadata


def get_url() -> str:
    """Obtém a URL do banco de dados a partir das configurações centrais."""
    settings = get_settings()
    return settings.database_url


def run_migrations_offline() -> None:
    """Executa migrações no modo offline gerando SQL estático."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Executa as migrações dentro de uma transação ativa."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Cria conexão assíncrona e executa as migrações online."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Ponto de entrada para execução de migrações em modo online."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
