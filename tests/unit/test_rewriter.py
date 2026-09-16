"""Testes unitários para o módulo de reescrita contextual de queries multi-turn (FEAT-08)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from lumi.core.config import Settings
from lumi.rag.rewriter import QueryRewriter


@pytest.fixture
def mock_llm() -> MagicMock:
    """Fixture com mock de BaseChatModel suportando ainvoke."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def sample_chat_history() -> list[HumanMessage | AIMessage]:
    """Fixture com histórico prévio de diálogo técnico."""
    return [
        HumanMessage(content="Qual o critério para ramais de entrada segundo a DIS-NOR-030?"),
        AIMessage(
            content="Segundo a DIS-NOR-030, item 5.2, os ramais devem suportar a demanda calculada com condutores de cobre."
        ),
    ]


class TestQueryRewriterBypass:
    """Testes de bypass do QueryRewriter sem chamada à LLM."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("empty_history", [None, []])
    async def test_bypass_on_first_turn(
        self,
        mock_llm: MagicMock,
        empty_history: list | None,
    ) -> None:
        """Garante bypass imediato no 1º turno (sem histórico prévio), sem acionar a LLM."""
        rewriter = QueryRewriter(llm=mock_llm)
        query = "Como calcular a demanda de um edifício?"

        result = await rewriter.rewrite(query=query, chat_history=empty_history)

        assert result == query
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_bypass_when_rewriter_disabled(
        self,
        mock_llm: MagicMock,
        sample_chat_history: list,
    ) -> None:
        """Garante bypass quando a flag query_rewriter_enabled=False nas configurações."""
        settings = Settings(query_rewriter_enabled=False)
        rewriter = QueryRewriter(llm=mock_llm, settings=settings)
        query = "E se o ramal for aéreo?"

        result = await rewriter.rewrite(query=query, chat_history=sample_chat_history)

        assert result == query
        mock_llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("empty_query", ["", "   ", "\t \n "])
    async def test_bypass_empty_or_whitespace_query(
        self,
        mock_llm: MagicMock,
        sample_chat_history: list,
        empty_query: str,
    ) -> None:
        """Garante bypass defensivo para query vazia ou whitespace sem invocar a LLM."""
        rewriter = QueryRewriter(llm=mock_llm)

        result = await rewriter.rewrite(query=empty_query, chat_history=sample_chat_history)

        assert result == empty_query.strip()
        mock_llm.ainvoke.assert_not_called()


class TestQueryRewriterExecution:
    """Testes de execução contextual e fallback do QueryRewriter."""

    @pytest.mark.asyncio
    async def test_rewrite_multi_turn_success(
        self,
        mock_llm: MagicMock,
        sample_chat_history: list,
    ) -> None:
        """Testa reescrita contextual bem-sucedida resolvendo anáforas e normas."""
        rewritten_expected = (
            "Qual o critério para ramal aéreo segundo a norma DIS-NOR-030 da Neoenergia?"
        )
        mock_response = MagicMock()
        mock_response.content = rewritten_expected
        mock_llm.ainvoke.return_value = mock_response

        settings = Settings(query_rewriter_enabled=True)
        rewriter = QueryRewriter(llm=mock_llm, settings=settings)
        query = "E se o ramal for aéreo?"

        result = await rewriter.rewrite(query=query, chat_history=sample_chat_history)

        assert result == rewritten_expected
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_rewrite_fallback_on_llm_exception(
        self,
        mock_llm: MagicMock,
        sample_chat_history: list,
    ) -> None:
        """Testa fallback gracioso para a query original quando a LLM levanta exceção."""
        mock_llm.ainvoke.side_effect = RuntimeError("Conexão com Gemini/Claude falhou")

        settings = Settings(query_rewriter_enabled=True)
        rewriter = QueryRewriter(llm=mock_llm, settings=settings)
        query = "Qual tabela utilizar para esse caso?"

        result = await rewriter.rewrite(query=query, chat_history=sample_chat_history)

        # Deve retornar a query original limpa sem propagar a exceção
        assert result == query.strip()
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_rewrite_strips_enclosing_quotes_and_whitespace(
        self,
        mock_llm: MagicMock,
        sample_chat_history: list,
    ) -> None:
        """Garante que aspas extras geradas pelo modelo sejam sanitizadas."""
        mock_response = MagicMock()
        mock_response.content = '  "Qual a proteção para ramal subterrâneo na DIS-NOR-030?" \n'
        mock_llm.ainvoke.return_value = mock_response

        rewriter = QueryRewriter(llm=mock_llm)
        query = "E se for subterrâneo?"

        result = await rewriter.rewrite(query=query, chat_history=sample_chat_history)

        assert result == "Qual a proteção para ramal subterrâneo na DIS-NOR-030?"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("empty_response", ["", "   ", '""', "''"])
    async def test_rewrite_empty_llm_response_fallback(
        self,
        mock_llm: MagicMock,
        sample_chat_history: list,
        empty_response: str,
    ) -> None:
        """Garante fallback para query original quando a resposta da LLM é vazia ou apenas aspas."""
        mock_response = MagicMock()
        mock_response.content = empty_response
        mock_llm.ainvoke.return_value = mock_response

        rewriter = QueryRewriter(llm=mock_llm)
        query = "Qual a seção mínima?"

        result = await rewriter.rewrite(query=query, chat_history=sample_chat_history)

        assert result == query

