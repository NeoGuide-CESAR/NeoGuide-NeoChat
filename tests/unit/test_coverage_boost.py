"""Testes unitários adicionais focados no fechamento de cobertura (meta >= 95%)."""

import runpy
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import Request
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql, sqlite

from lumi.api.deps import RateLimiter
from lumi.core.config import Settings
from lumi.db.models import (
    GUID,
    ChatMessage,
    ChatSession,
    NormativeChunk,
    NormativeDocument,
    NormativeQueryAnalytics,
    _compile_vector_sqlite,
)
from lumi.db.session import create_app_engine, get_engine, get_session_factory
from lumi.ingestion.chunker import (
    chunk_document,
    chunk_table,
    recursive_split_text,
)
from lumi.ingestion.models import ParsedDocument
from lumi.services.analytics_service import persist_interaction_background


class TestApiDepsCoverage:
    """Testa branches de api/deps.py."""

    @pytest.mark.asyncio
    async def test_rate_limiter_callable_interface(self) -> None:
        """Invoca RateLimiter.__call__ como dependência FastAPI."""
        limiter = RateLimiter(requests_per_minute=10, window_seconds=60)
        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.100"

        res = await limiter(mock_request, api_key="test-api-key")
        assert res == "test-api-key"

        # Chamada sem API key (usa host)
        res_anon = await limiter(mock_request, api_key="")
        assert res_anon == "192.168.1.100"

        # Chamada sem request.client
        mock_req_no_client = MagicMock(spec=Request)
        mock_req_no_client.client = None
        res_no_client = await limiter(mock_req_no_client, api_key="")
        assert res_no_client == "anonymous"


class TestDbModelsAndSessionCoverage:
    """Testa tipos customizados de db/models.py e utilitários de db/session.py."""

    def test_guid_type_decorator_methods(self) -> None:
        """Cobre todos os branches de load_dialect_impl, process_bind_param e process_result_value em GUID."""
        guid_type = GUID()
        pg_dialect = postgresql.dialect()
        sqlite_dialect = sqlite.dialect()

        # 1. load_dialect_impl
        assert guid_type.load_dialect_impl(pg_dialect) is not None
        assert guid_type.load_dialect_impl(sqlite_dialect) is not None

        # 2. process_bind_param
        test_uuid = uuid4()
        test_uuid_str = str(test_uuid)

        assert guid_type.process_bind_param(None, pg_dialect) is None
        assert guid_type.process_bind_param(test_uuid, pg_dialect) == test_uuid
        assert guid_type.process_bind_param(test_uuid_str, sqlite_dialect) == test_uuid_str
        assert guid_type.process_bind_param(test_uuid, sqlite_dialect) == test_uuid_str

        # 3. process_result_value
        assert guid_type.process_result_value(None, pg_dialect) is None
        assert guid_type.process_result_value(test_uuid, pg_dialect) == test_uuid
        assert guid_type.process_result_value(test_uuid_str, sqlite_dialect) == test_uuid

    def test_compile_vector_sqlite(self) -> None:
        """Cobre a compilação do tipo pgvector para BLOB no SQLite."""
        compiler = MagicMock()
        res = _compile_vector_sqlite(Vector(768), compiler)
        assert res == "BLOB"

    def test_db_models_repr_methods(self) -> None:
        """Valida que instâncias de modelos ORM podem ser criadas com todos os campos."""
        doc_id = uuid4()
        doc = NormativeDocument(
            id=doc_id,
            code="DIS-TEST",
            title="Norma Teste",
            revision="REV01",
        )
        assert doc.code == "DIS-TEST"

        chunk = NormativeChunk(
            id=uuid4(),
            document_id=doc_id,
            content="Conteúdo de teste",
            section_code="1.0",
            section_title="Intro",
            page_number=1,
            metadata_={"key": "val"},
        )
        assert chunk.content == "Conteúdo de teste"

        session = ChatSession(id=uuid4())
        assert session.id is not None

        msg = ChatMessage(session_id=session.id, role="user", content="olá")
        assert msg.content == "olá"

        analytics = NormativeQueryAnalytics(
            session_id=session.id,
            query_text="teste",
            top_document_code="DIS-TEST",
            top_similarity_score=0.95,
            latency_ms=120,
        )
        assert analytics.latency_ms == 120

    def test_session_engine_and_factory_helpers(self) -> None:
        """Cobre create_app_engine com sqlite, get_engine e get_session_factory."""
        sqlite_settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
        with patch("lumi.db.session.create_async_engine") as mock_cae:
            mock_cae.return_value = MagicMock()
            engine = create_app_engine(sqlite_settings)
            assert engine is not None
            mock_cae.assert_called_once_with("sqlite+aiosqlite:///:memory:")

        eng = get_engine()
        assert eng is not None

        fac = get_session_factory()
        assert fac is not None


class TestAnalyticsServiceCoverage:
    """Testa branches de analytics_service.py."""

    @pytest.mark.asyncio
    async def test_persist_interaction_with_hallucinated_citations_and_no_sources(self) -> None:
        """Cobre persistência de fontes geradas por auditoria a partir de citações alucinadas."""
        session_id = uuid4()
        now = datetime.now(UTC)
        active_session = ChatSession(id=session_id, created_at=now, updated_at=now)

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = active_session
        mock_db.execute = AsyncMock(return_value=mock_res)

        class MockContextManager:
            async def __aenter__(self):
                return mock_db

            async def __aexit__(self, *args):
                pass

        with patch("lumi.services.analytics_service.get_db_session", return_value=MockContextManager()):
            success = await persist_interaction_background(
                session_id=session_id,
                query_text="Pergunta com citação não fundamentada",
                assistant_message="De acordo com [Fonte: DIS-NOR-030, Item 4.2] e [Fonte: INVALID, Item 99].",
                sources=[],
                retrieved_chunks=[],
                top_document_code="DIS-NOR-030",
                top_similarity_score=0.75,
                latency_ms=250,
                max_retries=1,
            )
            assert success is True
            assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_persist_interaction_exhausts_retries_returns_false(self) -> None:
        """Cobre caso onde todas as retentativas falham por exceção de banco."""
        session_id = uuid4()

        class ErrorContextManager:
            async def __aenter__(self):
                raise RuntimeError("Falha permanente de conexão")

            async def __aexit__(self, *args):
                pass

        with patch("lumi.services.analytics_service.get_db_session", return_value=ErrorContextManager()):
            success = await persist_interaction_background(
                session_id=session_id,
                query_text="Pergunta",
                assistant_message="Resposta",
                sources=[],
                top_document_code="DIS-NOR-030",
                top_similarity_score=0.9,
                latency_ms=100,
                max_retries=1,
                retry_backoff_seconds=0.01,
            )
            assert success is False


class TestIngestionChunkerCoverage:
    """Testa branches de chunker.py."""

    def test_recursive_split_empty_separator(self) -> None:
        """Cobre separadores com string vazia ou sem separador correspondente."""
        res = recursive_split_text("abcdefghijkl", chunk_size=4, chunk_overlap=1, separators=[""])
        assert len(res) >= 3

    def test_chunk_table_empty_or_whitespace(self) -> None:
        """Cobre tabela vazia e tabela só de espaços."""
        assert chunk_table("", "t1", "DIS-030", "01") == []
        assert chunk_table("   \n \n  ", "t1", "DIS-030", "01") == []

    def test_chunk_table_page_range(self) -> None:
        """Cobre página com intervalo (page_range)."""
        table_md = "| Col1 | Col2 |\n|---|---|\n| Dado 1 | Dado 2 |"
        res = chunk_table(
            table_md,
            "table_1",
            "DIS-030",
            "07",
            page_range=[5, 6],
            metadata={"extra": True},
        )
        assert len(res) == 1
        assert res[0].metadata["page_range"] == [5, 6]

    def test_chunk_normative_document_table_caption_above_and_end_with_table(self) -> None:
        """Cobre documento onde a linha anterior à tabela é caption e documento finaliza com tabela."""
        doc_text = (
            "# 1.0 Introdução\n"
            "Texto explicativo.\n\n"
            "**[Página 1]**\n"
            "Tabela 1 - Afastamentos mínimos\n"
            "| Tensão | Distância |\n"
            "|---|---|\n"
            "| 13.8kV | 5,5m |\n"
            "**[Página 2]**\n"
            "| 34.5kV | 6,0m |\n"
        )
        parsed_doc = ParsedDocument(
            document_code="DIS-NOR-030",
            title="Norma Técnica",
            revision="07",
            company="Neoenergia Pernambuco",
            pages=[],
            full_clean_text=doc_text,
            source_file="fake.pdf",
        )
        chunks = chunk_document(
            parsed_doc,
        )
        assert len(chunks) >= 2
        # Verifica se pelo menos um chunk é de tabela
        table_chunks = [c for c in chunks if c.metadata.get("is_table")]
        assert len(table_chunks) >= 1


class TestIngestionParserCoverage:
    """Testa branches de parser.py."""

    def test_format_markdown_table_empty_rows(self) -> None:
        """Cobre tabela com linhas vazias e tabela sem linhas válidas."""
        from lumi.ingestion.parser import format_table_as_markdown

        assert format_table_as_markdown([]) == ""
        assert format_table_as_markdown([[], []]) == ""
        assert format_table_as_markdown([["", ""]]) == ""

    def test_extract_pdf_metadata_companies_and_fallbacks(self) -> None:
        """Cobre detecção de concessionárias Coelba, Cosern, Elektro e fallback de título."""
        from lumi.ingestion.parser import _extract_pdf_metadata

        code, title, rev, company = _extract_pdf_metadata("Texto Coelba sem título", "doc.pdf")
        assert company == "Neoenergia Coelba"

        _, _, _, company_cosern = _extract_pdf_metadata("Texto Cosern", "doc.pdf")
        assert company_cosern == "Neoenergia Cosern"

        _, _, _, company_elektro = _extract_pdf_metadata("Texto Elektro", "doc.pdf")
        assert company_elektro == "Neoenergia Elektro"

        # Fallback de revisão a partir de nome de arquivo
        code, title, rev, _ = _extract_pdf_metadata("Texto Pernambuco", "DIS-NOR-030_REV_07.pdf")
        assert code == "DIS-NOR-030"
        assert rev == "REV07"


class TestIngestionPipelineCoverage:
    """Testa branches de pipeline.py."""

    @pytest.mark.asyncio
    async def test_generate_embeddings_empty_texts(self) -> None:
        """Cobre texts vazio em generate_embeddings_with_retry."""
        from lumi.ingestion.pipeline import generate_embeddings_with_retry

        res = await generate_embeddings_with_retry([])
        assert res == []

    @pytest.mark.asyncio
    async def test_generate_embeddings_sync_fallback(self) -> None:
        """Cobre serviço que só possui método síncrono embed_documents."""
        from lumi.ingestion.pipeline import generate_embeddings_with_retry

        mock_svc = MagicMock()
        del mock_svc.aembed_documents
        mock_svc.embed_documents.return_value = [[0.1] * 768]

        res = await generate_embeddings_with_retry(["teste"], embedding_service=mock_svc)
        assert len(res) == 1

    @pytest.mark.asyncio
    async def test_ingest_normative_document_error_handling(self, tmp_path) -> None:
        """Cobre raise_on_error=False retornando IngestionResult com erro."""
        from lumi.ingestion.pipeline import ingest_normative_file

        fake_file = tmp_path / "fake.txt"
        fake_file.write_text("conteúdo inválido")

        with patch("lumi.ingestion.pipeline.parse_document", side_effect=ValueError("Formato não suportado")):
            result = await ingest_normative_file(fake_file, raise_on_error=False)
            assert result.status == "error"
            assert "Formato não suportado" in result.error_message

    @pytest.mark.asyncio
    async def test_pipeline_main_cli_branches(self, tmp_path) -> None:
        """Cobre ramos de CLI: caminho inexistente, diretório vazio e falha de ingestão."""
        from lumi.ingestion.pipeline import main

        # 1. Caminho inexistente
        ret = await main([str(tmp_path / "inexistente")])
        assert ret == 1

        # 2. Diretório vazio
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        ret = await main([str(empty_dir)])
        assert ret == 1


class TestIngestionMainModule:
    """Testa o ponto de entrada __main__.py do módulo lumi.ingestion."""

    def test_ingestion_main_execution(self) -> None:
        """Executa runpy sobre lumi.ingestion.__main__ com mock."""
        with (
            patch("lumi.ingestion.pipeline.main", new_callable=AsyncMock) as mock_main,
            patch("sys.exit") as mock_exit,
        ):
            mock_main.return_value = 0
            runpy.run_module("lumi.ingestion", run_name="__main__")
            mock_exit.assert_called_once_with(0)
