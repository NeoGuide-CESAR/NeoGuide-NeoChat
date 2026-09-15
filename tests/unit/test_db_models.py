"""Testes unitários para modelos SQLAlchemy, índices, metadados e ciclo de vida de sessões."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pgvector.sqlalchemy import Vector
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.api.deps import get_db as deps_get_db
from lumi.api.deps import get_db_session as deps_get_db_session
from lumi.db import (
    Base,
    ChatMessage,
    ChatSession,
    NormativeChunk,
    NormativeDocument,
    NormativeQueryAnalytics,
    get_db,
    get_db_session,
)
from lumi.db.session import create_app_engine


class TestDatabaseMetadata:
    """Verifica o registro correto das tabelas e esquemas no Base.metadata."""

    def test_all_five_tables_registered_in_metadata(self) -> None:
        """Garante que as 5 tabelas requisitadas estão registradas no SQLAlchemy Base."""
        expected_tables = {
            "normative_documents",
            "normative_chunks",
            "chat_sessions",
            "chat_messages",
            "normative_query_analytics",
        }
        assert expected_tables.issubset(set(Base.metadata.tables.keys()))

    def test_normative_documents_columns(self) -> None:
        """Valida as colunas, restrições e unicidade de normative_documents."""
        table = Base.metadata.tables["normative_documents"]
        column_names = {col.name for col in table.columns}
        assert {"id", "code", "title", "revision", "created_at"}.issubset(column_names)

        # Valida constraint de unicidade no código da norma
        code_col = table.columns["code"]
        assert code_col.unique is True or any(
            idx.unique and "code" in [c.name for c in idx.columns] for idx in table.indexes
        )
        assert code_col.nullable is False

    def test_normative_chunks_columns_and_embedding(self) -> None:
        """Valida colunas de normative_chunks, tipo Vector(768) e mapeamento de metadata."""
        table = Base.metadata.tables["normative_chunks"]
        column_names = {col.name for col in table.columns}
        assert {
            "id",
            "document_id",
            "content",
            "embedding",
            "section_code",
            "section_title",
            "page_number",
            "metadata",
        }.issubset(column_names)

        # Valida tipo da coluna embedding como Vector de 768 dimensões
        embedding_col = table.columns["embedding"]
        assert isinstance(embedding_col.type, Vector)
        assert embedding_col.type.dim == 768

        # Valida foreign key com cascade delete
        fks = list(table.foreign_keys)
        doc_fk = next(fk for fk in fks if fk.column.table.name == "normative_documents")
        assert doc_fk.ondelete == "CASCADE"

        # Valida mapeamento do atributo Python metadata_ para o nome físico de coluna 'metadata'
        mapper = inspect(NormativeChunk)
        attr = mapper.attrs["metadata_"]
        assert attr.columns[0].name == "metadata"

    def test_normative_chunks_hnsw_index(self) -> None:
        """Valida definição do índice HNSW com métrica de cosseno."""
        table = Base.metadata.tables["normative_chunks"]
        hnsw_indexes = [
            idx
            for idx in table.indexes
            if idx.dialect_options.get("postgresql", {}).get("using") == "hnsw"
            or "hnsw" in idx.name
        ]
        assert len(hnsw_indexes) >= 1
        hnsw_idx = hnsw_indexes[0]
        pg_opts = hnsw_idx.dialect_options.get("postgresql", {})
        assert pg_opts.get("using") == "hnsw"
        assert pg_opts.get("with") == {"m": 16, "ef_construction": 64}
        assert pg_opts.get("ops") == {"embedding": "vector_cosine_ops"}

    def test_chat_sessions_columns_and_relationships(self) -> None:
        """Valida colunas de chat_sessions e relacionamento cascade."""
        table = Base.metadata.tables["chat_sessions"]
        column_names = {col.name for col in table.columns}
        assert {"id", "created_at", "updated_at"}.issubset(column_names)

        mapper = inspect(ChatSession)
        rel = mapper.relationships["messages"]
        assert rel.cascade.delete is True
        assert rel.cascade.delete_orphan is True

    def test_chat_messages_columns_and_composite_index(self) -> None:
        """Valida colunas e índice composto B-Tree temporal em chat_messages."""
        table = Base.metadata.tables["chat_messages"]
        column_names = {col.name for col in table.columns}
        assert {"id", "session_id", "role", "content", "sources", "created_at"}.issubset(
            column_names
        )

        # Valida foreign key
        fks = list(table.foreign_keys)
        session_fk = next(fk for fk in fks if fk.column.table.name == "chat_sessions")
        assert session_fk.ondelete == "CASCADE"

        # Valida índice composto (session_id, created_at)
        composite_indexes = [
            idx
            for idx in table.indexes
            if [c.name for c in idx.columns] == ["session_id", "created_at"]
        ]
        assert len(composite_indexes) == 1

    def test_normative_query_analytics_columns(self) -> None:
        """Valida colunas e foreign key opcional de normative_query_analytics."""
        table = Base.metadata.tables["normative_query_analytics"]
        column_names = {col.name for col in table.columns}
        assert {
            "id",
            "session_id",
            "query_text",
            "top_document_code",
            "top_similarity_score",
            "latency_ms",
            "created_at",
        }.issubset(column_names)

        # Valida FK SET NULL
        fks = list(table.foreign_keys)
        session_fk = next(fk for fk in fks if fk.column.table.name == "chat_sessions")
        assert session_fk.ondelete == "SET NULL"


class TestModelInstantiation:
    """Verifica instanciação e integridade de objetos dos modelos em memória."""

    def test_instantiate_normative_document_and_chunk(self) -> None:
        doc = NormativeDocument(
            code="DIS-NOR-030",
            title="Critérios de Projeto de Redes Aéreas",
            revision="REV07",
        )
        assert doc.id is not None
        assert doc.code == "DIS-NOR-030"

        chunk = NormativeChunk(
            document_id=doc.id,
            content="Instalação de postes de telecomunicação em faixa de servidão.",
            embedding=[0.1] * 768,
            section_code="Item 4.2",
            section_title="Distanciamento",
            page_number=15,
            metadata_={"tag": "redes_aereas"},
        )
        assert chunk.id is not None
        assert chunk.document_id == doc.id
        assert chunk.metadata_["tag"] == "redes_aereas"

    def test_instantiate_chat_session_and_message(self) -> None:
        session = ChatSession()
        assert session.id is not None

        msg = ChatMessage(
            session_id=session.id,
            role="user",
            content="Qual a distância mínima entre postes?",
            sources=[],
        )
        assert msg.id is not None
        assert msg.role == "user"

    def test_instantiate_query_analytics(self) -> None:
        analytics = NormativeQueryAnalytics(
            query_text="Qual a bitola mínima para cabos?",
            top_document_code="DIS-NOR-030",
            top_similarity_score=0.88,
            latency_ms=350,
        )
        assert analytics.id is not None
        assert analytics.latency_ms == 350
        assert analytics.session_id is None


class TestDatabaseSessionLifecycle:
    """Valida gerenciamento assíncrono de sessão, commit e rollback."""

    @pytest.mark.asyncio
    async def test_get_db_session_commit_on_success(self) -> None:
        """Garante que a sessão realiza commit e fecha quando não há erro."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = MagicMock(return_value=mock_session)

        async with get_db_session(session_factory=mock_factory) as session:
            assert session is mock_session

        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_awaited()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_db_session_rollback_on_exception(self) -> None:
        """Garante que a sessão realiza rollback e propaga a exceção se ocorrer falha."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = MagicMock(return_value=mock_session)

        with pytest.raises(RuntimeError, match="Erro de teste na transação"):
            async with get_db_session(session_factory=mock_factory):
                raise RuntimeError("Erro de teste na transação")

        mock_session.commit.assert_not_awaited()
        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_db_generator_for_fastapi_depends(self) -> None:
        """Garante que o gerador get_db() funciona com Depends do FastAPI."""
        gen = get_db()
        assert isinstance(gen, AsyncGenerator)

        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = MagicMock(return_value=mock_session)

        with patch("lumi.db.session.async_session_factory", mock_factory):
            async for s in get_db():
                assert s is mock_session

        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    def test_deps_re_exports_get_db(self) -> None:
        """Verifica se get_db e get_db_session estão re-exportados em lumi.api.deps."""
        assert deps_get_db is get_db
        assert deps_get_db_session is get_db_session

    def test_create_app_engine_pool_configuration(self) -> None:
        """Verifica se create_app_engine configura o pool com os parâmetros requisitados."""
        with patch("lumi.db.session.create_async_engine") as mock_create_engine:
            mock_settings = MagicMock()
            mock_settings.database_url = (
                "postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_db"
            )
            mock_settings.db_pool_size = 5
            mock_settings.db_max_overflow = 10
            mock_settings.db_pool_timeout = 30
            mock_settings.debug = False

            create_app_engine(mock_settings)

            mock_create_engine.assert_called_once_with(
                "postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_db",
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                echo=False,
            )


class TestAlembicMigrationStructure:
    """Verifica a integridade do arquivo de migração inicial do Alembic."""

    def test_migration_0001_initial_schema_attributes(self) -> None:
        """Garante que a migração inicial possui id, upgrade e downgrade válidos."""
        import importlib.util
        from pathlib import Path

        migration_path = (
            Path(__file__).parents[2] / "alembic" / "versions" / "0001_initial_schema.py"
        )
        assert migration_path.exists(), f"Arquivo não encontrado: {migration_path}"

        spec = importlib.util.spec_from_file_location("initial_schema_module", migration_path)
        assert spec is not None and spec.loader is not None
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        assert migration.revision == "0001_initial_schema"
        assert migration.down_revision is None
        assert callable(migration.upgrade)
        assert callable(migration.downgrade)
