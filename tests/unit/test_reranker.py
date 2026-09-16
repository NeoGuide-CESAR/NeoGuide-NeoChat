"""Testes unitários para o módulo de reranking semântico listwise (FEAT-08)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from lumi.core.config import Settings
from lumi.rag.reranker import NormativeReranker
from lumi.rag.retriever import RetrievedChunk


def make_chunk(doc_code: str, sec: str, score: float, content: str) -> RetrievedChunk:
    """Helper para instanciar RetrievedChunk nos testes."""
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
def mock_llm() -> MagicMock:
    """Fixture com mock de BaseChatModel suportando ainvoke."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def candidate_chunks() -> list[RetrievedChunk]:
    """Fixture com 6 chunks candidatos simulando resultado da busca vetorial."""
    return [
        make_chunk("DIS-NOR-030", "Item 1.0", 0.95, "Introdução e definições gerais de redes."),
        make_chunk("DIS-NOR-030", "Item 5.2", 0.92, "Dimensionamento de ramais de ligação aéreos."),
        make_chunk(
            "DIS-NOR-053", "Item 4.1", 0.88, "Instalações de entrada em edifícios coletivos."
        ),
        make_chunk("DIS-NOR-030", "Item 5.3", 0.85, "Dimensionamento de ramais subterrâneos."),
        make_chunk("DIS-NOR-053", "Item 6.3", 0.80, "Proteção e medição agrupada em condomínios."),
        make_chunk("DIS-NOR-030", "Item 8.0", 0.75, "Anexos e tabelas de queda de tensão."),
    ]


class TestNormativeRerankerBypass:
    """Testes de cenários de bypass do NormativeReranker sem acionar a LLM."""

    @pytest.mark.asyncio
    async def test_bypass_when_empty_chunks(self, mock_llm: MagicMock) -> None:
        """Retorna lista vazia imediatamente se não houver chunks candidatos."""
        reranker = NormativeReranker(llm=mock_llm)
        result = await reranker.rerank(query="Como calcular ramal?", chunks=[])

        assert result == []
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_bypass_when_reranker_disabled(
        self,
        mock_llm: MagicMock,
        candidate_chunks: list[RetrievedChunk],
    ) -> None:
        """Garante bypass quando reranker_enabled=False nas configurações."""
        settings = Settings(reranker_enabled=False, reranker_top_n=5)
        reranker = NormativeReranker(llm=mock_llm, settings=settings)

        result = await reranker.rerank(query="Qual o ramal aéreo?", chunks=candidate_chunks)

        assert len(result) == 5
        assert result == candidate_chunks[:5]
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_bypass_when_chunk_count_less_or_equal_top_n(
        self,
        mock_llm: MagicMock,
        candidate_chunks: list[RetrievedChunk],
    ) -> None:
        """Garante bypass se len(chunks) <= top_n, dispensando a chamada à LLM."""
        settings = Settings(reranker_enabled=True, reranker_top_n=5)
        reranker = NormativeReranker(llm=mock_llm, settings=settings)

        # Apenas 3 chunks fornecidos com top_n=5
        sub_chunks = candidate_chunks[:3]
        result = await reranker.rerank(query="Qual o ramal?", chunks=sub_chunks, top_n=5)

        assert result == sub_chunks
        mock_llm.ainvoke.assert_not_called()


class TestNormativeRerankerExecution:
    """Testes de execução de reranking listwise e tolerância a falhas."""

    @pytest.mark.asyncio
    async def test_rerank_listwise_success_json_array(
        self,
        mock_llm: MagicMock,
        candidate_chunks: list[RetrievedChunk],
    ) -> None:
        """Testa reordenação semântica quando a LLM retorna array JSON puro de índices."""
        # Candidatos: [0, 1, 2, 3, 4, 5]. LLM julga que 1 (ramal aéreo) e 3 (ramal subterrâneo) são mais relevantes
        mock_response = MagicMock()
        mock_response.content = "[1, 3, 4, 2, 0]"
        mock_llm.ainvoke.return_value = mock_response

        settings = Settings(reranker_enabled=True, reranker_top_n=5)
        reranker = NormativeReranker(llm=mock_llm, settings=settings)

        result = await reranker.rerank(
            query="Quais as regras para ramais?", chunks=candidate_chunks
        )

        assert len(result) == 5
        assert result[0].section_code == "Item 5.2"  # chunk 1
        assert result[1].section_code == "Item 5.3"  # chunk 3
        assert result[2].section_code == "Item 6.3"  # chunk 4
        assert result[3].section_code == "Item 4.1"  # chunk 2
        assert result[4].section_code == "Item 1.0"  # chunk 0
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_rerank_listwise_markdown_json_block(
        self,
        mock_llm: MagicMock,
        candidate_chunks: list[RetrievedChunk],
    ) -> None:
        """Testa parsing correto quando a LLM encapsula a resposta em bloco markdown ```json."""
        mock_response = MagicMock()
        mock_response.content = "```json\n[3, 1, 2]\n```"
        mock_llm.ainvoke.return_value = mock_response

        settings = Settings(reranker_enabled=True, reranker_top_n=3)
        reranker = NormativeReranker(llm=mock_llm, settings=settings)

        result = await reranker.rerank(query="Ramais?", chunks=candidate_chunks, top_n=3)

        assert len(result) == 3
        assert result[0] == candidate_chunks[3]
        assert result[1] == candidate_chunks[1]
        assert result[2] == candidate_chunks[2]

    @pytest.mark.asyncio
    async def test_rerank_fallback_on_llm_exception(
        self,
        mock_llm: MagicMock,
        candidate_chunks: list[RetrievedChunk],
    ) -> None:
        """Testa fallback gracioso para ordenação original quando a LLM lança exceção."""
        mock_llm.ainvoke.side_effect = TimeoutError("Timeout ao contatar modelo")

        settings = Settings(reranker_enabled=True, reranker_top_n=4)
        reranker = NormativeReranker(llm=mock_llm, settings=settings)

        result = await reranker.rerank(query="Qual o critério?", chunks=candidate_chunks, top_n=4)

        # Retorna os primeiros 4 chunks na ordem original de similaridade
        assert len(result) == 4
        assert result == candidate_chunks[:4]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_content",
        [
            "Não consegui ranquear esses fragmentos.",
            "{'indices': [0, 1]}",
            "```json\n[1, 2,\n```",
            "",
        ],
    )
    async def test_rerank_fallback_on_invalid_json(
        self,
        mock_llm: MagicMock,
        candidate_chunks: list[RetrievedChunk],
        invalid_content: str,
    ) -> None:
        """Testa fallback gracioso para ordenação original quando o retorno não é JSON de inteiros válido."""
        mock_response = MagicMock()
        mock_response.content = invalid_content
        mock_llm.ainvoke.return_value = mock_response

        settings = Settings(reranker_enabled=True, reranker_top_n=5)
        reranker = NormativeReranker(llm=mock_llm, settings=settings)

        result = await reranker.rerank(query="Qual o critério?", chunks=candidate_chunks)

        assert len(result) == 5
        assert result == candidate_chunks[:5]

    @pytest.mark.asyncio
    async def test_rerank_handles_out_of_bounds_and_duplicate_indices(
        self,
        mock_llm: MagicMock,
        candidate_chunks: list[RetrievedChunk],
    ) -> None:
        """Garante tratamento robusto para índices duplicados ou fora dos limites."""
        mock_response = MagicMock()
        # Índice 99 não existe; 1 está duplicado
        mock_response.content = "[99, 1, 1, -5, 3]"
        mock_llm.ainvoke.return_value = mock_response

        settings = Settings(reranker_enabled=True, reranker_top_n=4)
        reranker = NormativeReranker(llm=mock_llm, settings=settings)

        result = await reranker.rerank(query="Consulta", chunks=candidate_chunks, top_n=4)

        assert len(result) == 4
        # Deve priorizar os válidos [1, 3] e completar com os chunks restantes originais sem duplicar
        assert result[0] == candidate_chunks[1]
        assert result[1] == candidate_chunks[3]
        # Restantes preenchidos na ordem original
        assert result[2] == candidate_chunks[0]
        assert result[3] == candidate_chunks[2]
