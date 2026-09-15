"""Testes unitários para o repositório vetorial, pipeline de ingestão e CLI."""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.db.models import NormativeChunk, NormativeDocument
from lumi.db.vector_store import NormativeVectorStore
from lumi.ingestion.models import NormativeChunkData
from lumi.ingestion.pipeline import (
    IngestionResult,
    generate_embeddings_with_retry,
    ingest_normative_file,
)
from lumi.ingestion.pipeline import (
    main as cli_main,
)


def _make_sample_chunk(
    doc_code: str = "DIS-NOR-030",
    revision: str = "07",
    content: str = "Conteúdo de teste para infraestrutura elétrica.",
    section_code: str = "5.1",
    section_title: str = "Definições",
    page_number: int = 10,
    metadata: dict | None = None,
) -> NormativeChunkData:
    return NormativeChunkData(
        document_code=doc_code,
        revision=revision,
        content=content,
        section_code=section_code,
        section_title=section_title,
        page_number=page_number,
        metadata=metadata or {"is_table": False},
    )


class TestNormativeVectorStore:
    """Testes unitários para o repositório vetorial NormativeVectorStore."""

    @pytest.mark.asyncio
    async def test_upsert_document_creates_new_document_and_chunks(self) -> None:
        """Verifica criação de documento inédito e inserção em lote dos chunks."""
        mock_session = AsyncMock(spec=AsyncSession)
        # Simula que documento não existe previamente
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        store = NormativeVectorStore(mock_session)

        chunks_data = [
            _make_sample_chunk(content="Chunk 1", page_number=1),
            _make_sample_chunk(content="Chunk 2", page_number=2),
        ]
        embeddings = [[0.1] * 768, [0.2] * 768]

        inserted_count = await store.upsert_document_with_chunks(
            document_code="DIS-NOR-030",
            title="Norma Técnica DIS-NOR-030",
            revision="07",
            chunks_data=chunks_data,
            embeddings=embeddings,
        )

        assert inserted_count == 2
        mock_session.add.assert_called_once()
        mock_session.add_all.assert_called_once()
        added_chunks = mock_session.add_all.call_args[0][0]
        assert len(added_chunks) == 2
        assert isinstance(added_chunks[0], NormativeChunk)
        assert added_chunks[0].content == "Chunk 1"
        assert added_chunks[0].embedding == [0.1] * 768
        assert added_chunks[0].metadata_ == {"is_table": False}
        assert mock_session.flush.await_count >= 1

    @pytest.mark.asyncio
    async def test_upsert_document_idempotency_deletes_prior_chunks(self) -> None:
        """Garante que a re-ingestão de documento existente remove os chunks anteriores."""
        mock_session = AsyncMock(spec=AsyncSession)
        existing_doc = NormativeDocument(
            id=uuid.uuid4(),
            code="DIS-NOR-030",
            title="Título Antigo",
            revision="06",
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_doc
        mock_session.execute.return_value = mock_result

        store = NormativeVectorStore(mock_session)

        chunks_data = [_make_sample_chunk(content="Novo Chunk", revision="07")]
        embeddings = [[0.5] * 768]

        inserted_count = await store.upsert_document_with_chunks(
            document_code="DIS-NOR-030",
            title="Novo Título",
            revision="07",
            chunks_data=chunks_data,
            embeddings=embeddings,
        )

        assert inserted_count == 1
        assert existing_doc.title == "Novo Título"
        assert existing_doc.revision == "07"
        # Deve ter executado delete(NormativeChunk)
        assert mock_session.execute.await_count >= 2
        mock_session.add_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_mismatched_chunks_and_embeddings_raises_error(self) -> None:
        """Garante erro ao tentar upsert com contagens divergentes de chunks e embeddings."""
        mock_session = AsyncMock(spec=AsyncSession)
        store = NormativeVectorStore(mock_session)

        chunks_data = [_make_sample_chunk()]
        embeddings = [[0.1] * 768, [0.2] * 768]

        with pytest.raises(ValueError, match="divergentes"):
            await store.upsert_document_with_chunks(
                document_code="DIS-NOR-030",
                title="Norma",
                revision="07",
                chunks_data=chunks_data,
                embeddings=embeddings,
            )

    @pytest.mark.asyncio
    async def test_search_similar_executes_query_and_formats_results(self) -> None:
        """Verifica a busca de similaridade e formatação de resultados com score."""
        mock_session = AsyncMock(spec=AsyncSession)
        chunk1 = NormativeChunk(
            id=uuid.uuid4(),
            content="Instalação de postes em rede aérea",
            metadata_={},
        )
        chunk2 = NormativeChunk(
            id=uuid.uuid4(),
            content="Distâncias de segurança em linhas",
            metadata_={},
        )

        mock_result = MagicMock()
        # Simula retorno de tuplas (chunk, similarity)
        mock_result.all.return_value = [(chunk1, 0.88), (chunk2, 0.76)]
        mock_session.execute.return_value = mock_result

        store = NormativeVectorStore(mock_session)
        query_vector = [0.1] * 768

        results = await store.search_similar(
            query_embedding=query_vector,
            top_k=5,
            threshold=0.70,
            document_code="DIS-NOR-030",
        )

        assert len(results) == 2
        assert results[0][0] is chunk1
        assert results[0][1] == pytest.approx(0.88)
        assert results[1][0] is chunk2
        assert results[1][1] == pytest.approx(0.76)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_similar_empty_query_or_zero_top_k(self) -> None:
        """Verifica comportamento com vetor de busca vazio ou top_k zero."""
        mock_session = AsyncMock(spec=AsyncSession)
        store = NormativeVectorStore(mock_session)

        res1 = await store.search_similar([], top_k=5)
        assert res1 == []

        res2 = await store.search_similar([0.1] * 768, top_k=0)
        assert res2 == []
        mock_session.execute.assert_not_awaited()


class TestEmbeddingsBatchingAndRetry:
    """Testes para loteamento e retentativas com backoff exponencial."""

    @pytest.mark.asyncio
    async def test_batching_splits_and_preserves_order(self) -> None:
        """Garante que textos são fatiados em lotes do tamanho especificado."""
        texts = [f"Texto {i}" for i in range(70)]
        mock_embeddings = AsyncMock()
        # Retorna embeddings falsos para cada chamada
        mock_embeddings.aembed_documents.side_effect = lambda batch: [
            [0.1 * len(t)] * 768 for t in batch
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            results = await generate_embeddings_with_retry(
                texts=texts,
                batch_size=32,
                embedding_service=mock_embeddings,
                batch_delay=0.2,
            )

        assert len(results) == 70
        assert mock_embeddings.aembed_documents.await_count == 3  # 32 + 32 + 6
        # Pausa defensiva deve ser chamada 2 vezes (entre os lotes 1->2 e 2->3)
        assert mock_sleep.await_count == 2
        mock_sleep.assert_awaited_with(0.2)

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure_with_exponential_backoff(self) -> None:
        """Garante até 3 tentativas com backoff exponencial (1s, 2s, 4s) em falhas transitórias."""
        texts = ["Texto com erro transitório"]
        mock_embeddings = AsyncMock()
        # Falha 2 vezes e sucede na 3ª tentativa
        mock_embeddings.aembed_documents.side_effect = [
            RuntimeError("429 Too Many Requests"),
            ConnectionError("Conexão interrompida"),
            [[0.5] * 768],
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            results = await generate_embeddings_with_retry(
                texts=texts,
                batch_size=32,
                max_retries=3,
                retry_backoffs=(1.0, 2.0, 4.0),
                embedding_service=mock_embeddings,
            )

        assert len(results) == 1
        assert mock_embeddings.aembed_documents.await_count == 3
        # Esperou 1.0s e depois 2.0s
        assert mock_sleep.await_count == 2
        mock_sleep.assert_any_await(1.0)
        mock_sleep.assert_any_await(2.0)

    @pytest.mark.asyncio
    async def test_retries_exhausted_raises_exception(self) -> None:
        """Garante propagação de erro quando o limite de retentativas é esgotado."""
        texts = ["Texto falho permanente"]
        mock_embeddings = AsyncMock()
        mock_embeddings.aembed_documents.side_effect = RuntimeError("503 Service Unavailable")

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(RuntimeError, match="503 Service Unavailable"),
        ):
            await generate_embeddings_with_retry(
                texts=texts,
                batch_size=32,
                max_retries=3,
                retry_backoffs=(1.0, 2.0, 4.0),
                embedding_service=mock_embeddings,
            )


class TestIngestionPipeline:
    """Testes para a função orquestradora ingest_normative_file."""

    @pytest.mark.asyncio
    async def test_ingest_normative_file_markdown_success(self, tmp_path: Path) -> None:
        """Valida ingestão ponta a ponta de arquivo Markdown com provider fake."""
        test_file = tmp_path / "DIS-NOR-030-REV07.md"
        test_file.write_text(
            "# DIS-NOR-030 - CRITÉRIOS DE PROJETO\n"
            "Revisão: 07\n\n"
            "**[Página 1]**\n"
            "### 1. OBJETIVO\n"
            "Este documento estabelece critérios para redes de distribuição.\n\n"
            "**[Página 2]**\n"
            "### 2. APLICAÇÃO\n"
            "Aplica-se a todas as concessionárias do grupo Neoenergia.\n",
            encoding="utf-8",
        )

        mock_session = AsyncMock(spec=AsyncSession)
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_res

        result = await ingest_normative_file(
            file_path=test_file,
            provider="fake",
            batch_size=32,
            session=mock_session,
        )

        assert isinstance(result, IngestionResult)
        assert result.document_code == "DIS-NOR-030"
        assert result.revision in ("07", "REV07")
        assert result.total_chunks >= 2
        assert result.duration_seconds >= 0.0
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_ingest_normative_file_non_existent_raises_or_reports_error(self) -> None:
        """Valida que arquivo inexistente gera erro com status correspondente."""
        with pytest.raises(FileNotFoundError):
            await ingest_normative_file(
                file_path=Path("arquivo_inexistente.md"),
                provider="fake",
                raise_on_error=True,
            )


class TestIngestionCLI:
    """Testes para o ponto de entrada CLI lumi.ingestion.pipeline."""

    @pytest.mark.asyncio
    async def test_cli_single_file(self, tmp_path: Path) -> None:
        """Verifica a execução do CLI para arquivo único."""
        test_file = tmp_path / "DIS-NOR-053-REV06.md"
        test_file.write_text(
            "# DIS-NOR-053 - FORNECIMENTO DE ENERGIA\n"
            "Revisão: 06\n\n"
            "**[Página 1]**\n"
            "### 1. INTRODUÇÃO\n"
            "Norma para fornecimento em tensão secundária.\n",
            encoding="utf-8",
        )

        mock_session = AsyncMock(spec=AsyncSession)
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_res
        with (
            patch("lumi.ingestion.pipeline.get_db_session") as mock_get_session,
            patch("sys.argv", ["pipeline", str(test_file), "--provider", "fake"]),
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            exit_code = await cli_main()
            assert exit_code == 0

    @pytest.mark.asyncio
    async def test_cli_directory_with_all_flag(self, tmp_path: Path) -> None:
        """Verifica a execução recursiva do CLI em diretório com a flag --all."""
        file1 = tmp_path / "DIS-NOR-030-REV07.md"
        file1.write_text(
            "# DIS-NOR-030\nRevisão: 07\n\n**[Página 1]**\nTexto 1\n",
            encoding="utf-8",
        )
        file2 = tmp_path / "DIS-NOR-053-REV06.md"
        file2.write_text(
            "# DIS-NOR-053\nRevisão: 06\n\n**[Página 1]**\nTexto 2\n",
            encoding="utf-8",
        )

        mock_session = AsyncMock(spec=AsyncSession)
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_res
        with (
            patch("lumi.ingestion.pipeline.get_db_session") as mock_get_session,
            patch("sys.argv", ["pipeline", str(tmp_path), "--provider", "fake", "--all"]),
        ):
            mock_get_session.return_value.__aenter__.return_value = mock_session
            exit_code = await cli_main()
            assert exit_code == 0
