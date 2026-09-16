"""Testes unitários para o orquestrador contextual RagContextOrchestrator (FEAT-08)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from lumi.rag.chains import RagContextOrchestrator
from lumi.rag.prompts import CONTINGENCY_NO_SOURCES_MESSAGE
from lumi.rag.reranker import NormativeReranker
from lumi.rag.retriever import NormativeRetriever, RetrievalResult, RetrievedChunk
from lumi.rag.rewriter import QueryRewriter


def make_chunk(doc_code: str, sec: str, score: float, content: str) -> RetrievedChunk:
    """Helper para instanciar RetrievedChunk."""
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_code=doc_code,
        document_title="Norma Técnica",
        revision="REV01",
        section_code=sec,
        section_title="Seção",
        page_number=1,
        content=content,
        similarity_score=score,
    )


@pytest.fixture
def mock_retriever() -> MagicMock:
    """Fixture para mock de NormativeRetriever."""
    retriever = MagicMock(spec=NormativeRetriever)
    retriever.retrieve = AsyncMock()
    return retriever


@pytest.fixture
def mock_rewriter() -> MagicMock:
    """Fixture para mock de QueryRewriter."""
    rewriter = MagicMock(spec=QueryRewriter)
    rewriter.rewrite = AsyncMock()
    return rewriter


@pytest.fixture
def mock_reranker() -> MagicMock:
    """Fixture para mock de NormativeReranker."""
    reranker = MagicMock(spec=NormativeReranker)
    reranker.rerank = AsyncMock()
    return reranker


class TestRagContextOrchestrator:
    """Testes da pipeline de orquestração de contexto RAG."""

    @pytest.mark.asyncio
    async def test_full_pipeline_orchestration(
        self,
        mock_retriever: MagicMock,
        mock_rewriter: MagicMock,
        mock_reranker: MagicMock,
    ) -> None:
        """Testa o fluxo completo: histórico -> rewriter -> retriever -> reranker -> RetrievalResult."""
        history = [
            HumanMessage(content="Estou projetando um edifício residencial."),
            AIMessage(
                content="Certo! Para edifícios de múltiplas unidades aplicamos a DIS-NOR-053."
            ),
        ]
        raw_query = "E qual o ramal para 20 apartamentos?"
        rewritten_query = (
            "Qual o dimensionamento do ramal de entrada para 20 apartamentos na DIS-NOR-053?"
        )

        mock_rewriter.rewrite.return_value = rewritten_query

        chunk1 = make_chunk("DIS-NOR-053", "Item 4.1", 0.88, "Ramal de entrada coletivo")
        chunk2 = make_chunk("DIS-NOR-053", "Item 5.2", 0.85, "Dimensionamento para 20 unidades")
        retriever_result = RetrievalResult(
            query=rewritten_query,
            chunks=[chunk1, chunk2],
            is_contingency=False,
        )
        mock_retriever.retrieve.return_value = retriever_result

        # Reranker inverte a ordem
        reranked_chunks = [chunk2, chunk1]
        mock_reranker.rerank.return_value = reranked_chunks

        orchestrator = RagContextOrchestrator(
            retriever=mock_retriever,
            rewriter=mock_rewriter,
            reranker=mock_reranker,
        )

        final_result = await orchestrator.get_context(
            query=raw_query,
            chat_history=history,
            document_code="DIS-NOR-053",
        )

        # 1. Verifica chamada ao rewriter
        mock_rewriter.rewrite.assert_awaited_once_with(query=raw_query, chat_history=history)

        # 2. Verifica chamada ao retriever com a query reescrita e document_code
        mock_retriever.retrieve.assert_awaited_once_with(
            query=rewritten_query,
            document_code="DIS-NOR-053",
        )

        # 3. Verifica chamada ao reranker com chunks recuperados
        mock_reranker.rerank.assert_awaited_once_with(
            query=rewritten_query,
            chunks=[chunk1, chunk2],
        )

        # 4. Verifica resultado consolidado
        assert isinstance(final_result, RetrievalResult)
        assert final_result.query == rewritten_query
        assert final_result.chunks == reranked_chunks
        assert final_result.is_contingency is False
        assert final_result.contingency_message is None

    @pytest.mark.asyncio
    async def test_defensive_short_circuit_on_contingency(
        self,
        mock_retriever: MagicMock,
        mock_rewriter: MagicMock,
        mock_reranker: MagicMock,
    ) -> None:
        """Garante curto-circuito defensivo: se retriever retornar contingência, NÃO chama o reranker."""
        raw_query = "Qual a norma de iluminação pública?"
        mock_rewriter.rewrite.return_value = raw_query

        # Retriever retorna contingência
        contingency_result = RetrievalResult(
            query=raw_query,
            chunks=[],
            is_contingency=True,
            contingency_message=CONTINGENCY_NO_SOURCES_MESSAGE,
        )
        mock_retriever.retrieve.return_value = contingency_result

        orchestrator = RagContextOrchestrator(
            retriever=mock_retriever,
            rewriter=mock_rewriter,
            reranker=mock_reranker,
        )

        final_result = await orchestrator.get_context(query=raw_query)

        # O reranker NUNCA deve ser chamado quando houver contingência
        mock_reranker.rerank.assert_not_called()

        assert final_result.is_contingency is True
        assert final_result.contingency_message == CONTINGENCY_NO_SOURCES_MESSAGE
        assert final_result.chunks == []

    @pytest.mark.asyncio
    async def test_orchestration_without_optional_components(
        self,
        mock_retriever: MagicMock,
    ) -> None:
        """Garante operação resiliente quando rewriter e reranker forem omitidos (None)."""
        raw_query = "Como solicitar ligação nova?"
        chunk = make_chunk("DIS-NOR-030", "Item 3.0", 0.90, "Procedimento de ligação nova")
        retriever_result = RetrievalResult(
            query=raw_query,
            chunks=[chunk],
            is_contingency=False,
        )
        mock_retriever.retrieve.return_value = retriever_result

        # Inicializa apenas com o retriever obrigatório
        orchestrator = RagContextOrchestrator(
            retriever=mock_retriever,
            rewriter=None,
            reranker=None,
        )

        final_result = await orchestrator.get_context(query=raw_query)

        mock_retriever.retrieve.assert_awaited_once_with(
            query=raw_query,
            document_code=None,
        )
        assert final_result.query == raw_query
        assert final_result.chunks == [chunk]
        assert final_result.is_contingency is False

    @pytest.mark.asyncio
    async def test_orchestration_empty_chunks_skips_reranker(
        self,
        mock_retriever: MagicMock,
        mock_reranker: MagicMock,
    ) -> None:
        """Garante que se retriever retornar chunks vazios (não contingência), o reranker não é chamado."""
        retriever_result = RetrievalResult(
            query="Consulta",
            chunks=[],
            is_contingency=False,
        )
        mock_retriever.retrieve.return_value = retriever_result

        orchestrator = RagContextOrchestrator(
            retriever=mock_retriever,
            rewriter=None,
            reranker=mock_reranker,
        )

        final_result = await orchestrator.get_context(query="Consulta")

        mock_reranker.rerank.assert_not_called()
        assert final_result.chunks == []
