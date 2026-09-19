"""Testes unitários para a cadeia de fallback automático de modelos generativos Gemini (FEAT-16)."""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from langchain_core.messages import AIMessageChunk, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.core.config import Settings
from lumi.rag.chains import RagContextOrchestrator
from lumi.rag.llm_factory import (
    DEFAULT_GEMINI_FALLBACK_MODELS,
    DEFAULT_GEMINI_PRIMARY_MODEL,
    MAX_FALLBACK_ATTEMPTS,
    get_llm_chain,
    get_model_name,
)
from lumi.rag.retriever import RetrievalResult, RetrievedChunk
from lumi.rag.rewriter import QueryRewriter
from lumi.schemas.chat import ChatRequest
from lumi.services.chat_service import ChatService
from lumi.services.session_service import SessionService


def _create_mock_chat_model(model_name: str) -> MagicMock:
    """Cria um mock de BaseChatModel com atributos de identificação."""
    llm = MagicMock()
    llm.model = model_name
    llm.model_name = model_name
    llm.name = model_name
    return llm


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock da sessão assíncrona SQLAlchemy."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def test_settings() -> Settings:
    """Configurações controladas para testes com chaves e modelos padrão."""
    return Settings(
        gemini_api_key="mock-api-key",
        gemini_model="gemini-3.8-flash",
        gemini_fallback_models=["gemini-3.7-flash", "gemini-3.6-flash"],
        chat_history_limit=5,
        default_llm_provider="gemini",
    )


@pytest.fixture
def mock_session_service() -> AsyncMock:
    """Mock do SessionService ativo."""
    service = AsyncMock(spec=SessionService)
    service.get_session_or_raise.return_value = MagicMock()
    service.get_langchain_messages.return_value = []
    service.add_message.return_value = MagicMock()
    return service


@pytest.fixture
def mock_rag_orchestrator() -> AsyncMock:
    """Mock do RagContextOrchestrator com resultado normativo."""
    orchestrator = AsyncMock(spec=RagContextOrchestrator)
    sample_chunk = RetrievedChunk(
        chunk_id=uuid4(),
        document_code="DIS-NOR-030",
        document_title="Norma de Redes",
        revision="REV07",
        section_code="Item 4.1",
        section_title="Ramal",
        page_number=10,
        content="Conteúdo técnico sobre ramal.",
        similarity_score=0.85,
        metadata={},
    )
    orchestrator.get_context.return_value = RetrievalResult(
        query="qual a especificação do ramal?",
        chunks=[sample_chunk],
        is_contingency=False,
        contingency_message=None,
    )
    return orchestrator


class TestConfigAndFactoryDefaults:
    """Valida configurações de fallback e utilitários da fábrica."""

    def test_default_settings_models(self) -> None:
        """Valida se as configurações possuem os modelos e fallbacks padrão especificados."""
        settings = Settings()
        assert settings.gemini_model == "gemini-3.8-flash"
        assert settings.gemini_fallback_models == ["gemini-3.7-flash", "gemini-3.6-flash"]

    def test_factory_constants(self) -> None:
        """Valida constantes padrão na fábrica de LLMs."""
        assert DEFAULT_GEMINI_PRIMARY_MODEL == "gemini-3.8-flash"
        assert DEFAULT_GEMINI_FALLBACK_MODELS == ("gemini-3.7-flash", "gemini-3.6-flash")
        assert MAX_FALLBACK_ATTEMPTS == 3

    def test_get_model_name_extraction(self) -> None:
        """Valida extração correta do nome do modelo a partir de objetos e mocks."""
        mock1 = MagicMock()
        mock1.model = "gemini-3.8-flash"
        assert get_model_name(mock1) == "gemini-3.8-flash"

        mock2 = MagicMock(spec=[])
        mock2.model_name = "gemini-3.7-flash"
        assert get_model_name(mock2) == "gemini-3.7-flash"

        mock3 = MagicMock(spec=[])
        mock3.name = "gemini-3.6-flash"
        assert get_model_name(mock3) == "gemini-3.6-flash"

    def test_get_llm_chain_gemini_models(self, test_settings: Settings) -> None:
        """Valida que get_llm_chain gera a cadeia ordenada de 3 modelos Gemini."""
        chain = get_llm_chain(provider="gemini", settings=test_settings)
        assert len(chain) == 3
        assert chain[0].model == "gemini-3.8-flash"
        assert chain[1].model == "gemini-3.7-flash"
        assert chain[2].model == "gemini-3.6-flash"

    def test_get_llm_chain_respects_max_attempts_cap(self) -> None:
        """Garante que a cadeia de modelos não ultrapassa MAX_FALLBACK_ATTEMPTS (3)."""
        settings_extra = Settings(
            gemini_api_key="mock-key",
            gemini_model="gemini-3.8-flash",
            gemini_fallback_models=["gemini-3.7-flash", "gemini-3.6-flash", "gemini-1.5-flash"],
        )
        chain = get_llm_chain(provider="gemini", settings=settings_extra)
        assert len(chain) == MAX_FALLBACK_ATTEMPTS


class TestChatServiceSyncFallback:
    """Testes de fallback automático para invocação síncrona (process_chat)."""

    @pytest.mark.asyncio
    async def test_process_chat_success_on_primary(
        self,
        mock_db_session: AsyncMock,
        mock_session_service: AsyncMock,
        mock_rag_orchestrator: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Cenário 1: Sucesso no modelo primário 3.8 sem acionar fallbacks."""
        primary_llm = _create_mock_chat_model("gemini-3.8-flash")
        primary_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Resposta gerada pelo Gemini 3.8 Flash.")
        )

        fb1_llm = _create_mock_chat_model("gemini-3.7-flash")
        fb1_llm.ainvoke = AsyncMock()

        fb2_llm = _create_mock_chat_model("gemini-3.6-flash")
        fb2_llm.ainvoke = AsyncMock()

        chat_service = ChatService(
            session=mock_db_session,
            llm=primary_llm,
            fallback_llms=[fb1_llm, fb2_llm],
            rag_orchestrator=mock_rag_orchestrator,
            session_service=mock_session_service,
            settings=test_settings,
        )

        req = ChatRequest(session_id=uuid4(), message="Qual a norma para ramal?")

        with patch("lumi.services.chat_service.logger.warning") as mock_warn:
            response = await chat_service.process_chat(req)

            assert "Gemini 3.8 Flash" in response.response
            primary_llm.ainvoke.assert_called_once()
            fb1_llm.ainvoke.assert_not_called()
            fb2_llm.ainvoke.assert_not_called()
            mock_warn.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_chat_fallback_to_3_7_after_3_8_failure(
        self,
        mock_db_session: AsyncMock,
        mock_session_service: AsyncMock,
        mock_rag_orchestrator: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Cenário 2: Falha no primário (3.8) e recuperação transparente no 1º fallback (3.7)."""
        primary_llm = _create_mock_chat_model("gemini-3.8-flash")
        primary_llm.ainvoke = AsyncMock(
            side_effect=RuntimeError("HTTP 503: The model is overloaded. Please try again later.")
        )

        fb1_llm = _create_mock_chat_model("gemini-3.7-flash")
        fb1_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Resposta recuperada com sucesso pelo Gemini 3.7.")
        )

        fb2_llm = _create_mock_chat_model("gemini-3.6-flash")
        fb2_llm.ainvoke = AsyncMock()

        chat_service = ChatService(
            session=mock_db_session,
            llm=primary_llm,
            fallback_llms=[fb1_llm, fb2_llm],
            rag_orchestrator=mock_rag_orchestrator,
            session_service=mock_session_service,
            settings=test_settings,
        )

        req = ChatRequest(session_id=uuid4(), message="Qual a norma para ramal?")

        with patch("lumi.services.chat_service.logger.warning") as mock_warn:
            response = await chat_service.process_chat(req)

            assert "Gemini 3.7" in response.response
            primary_llm.ainvoke.assert_called_once()
            fb1_llm.ainvoke.assert_called_once()
            fb2_llm.ainvoke.assert_not_called()

            # Valida log estruturado emitido
            mock_warn.assert_called_once_with(
                "llm_fallback_attempt",
                failed_model="gemini-3.8-flash",
                next_model="gemini-3.7-flash",
                attempt=1,
                error=ANY,
            )

    @pytest.mark.asyncio
    async def test_process_chat_fallback_to_3_6_after_3_8_and_3_7_failure(
        self,
        mock_db_session: AsyncMock,
        mock_session_service: AsyncMock,
        mock_rag_orchestrator: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Cenário 3: Falhas em 3.8 e 3.7 com recuperação no 2º fallback (3.6) na 3ª tentativa."""
        primary_llm = _create_mock_chat_model("gemini-3.8-flash")
        primary_llm.ainvoke = AsyncMock(side_effect=RuntimeError("503 Service Unavailable"))

        fb1_llm = _create_mock_chat_model("gemini-3.7-flash")
        fb1_llm.ainvoke = AsyncMock(side_effect=RuntimeError("429 Resource Exhausted"))

        fb2_llm = _create_mock_chat_model("gemini-3.6-flash")
        fb2_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Resposta gerada pelo Gemini 3.6.")
        )

        chat_service = ChatService(
            session=mock_db_session,
            llm=primary_llm,
            fallback_llms=[fb1_llm, fb2_llm],
            rag_orchestrator=mock_rag_orchestrator,
            session_service=mock_session_service,
            settings=test_settings,
        )

        req = ChatRequest(session_id=uuid4(), message="Qual a norma para ramal?")

        with patch("lumi.services.chat_service.logger.warning") as mock_warn:
            response = await chat_service.process_chat(req)

            assert "Gemini 3.6" in response.response
            primary_llm.ainvoke.assert_called_once()
            fb1_llm.ainvoke.assert_called_once()
            fb2_llm.ainvoke.assert_called_once()

            assert mock_warn.call_count == 2
            mock_warn.assert_any_call(
                "llm_fallback_attempt",
                failed_model="gemini-3.8-flash",
                next_model="gemini-3.7-flash",
                attempt=1,
                error=ANY,
            )
            mock_warn.assert_any_call(
                "llm_fallback_attempt",
                failed_model="gemini-3.7-flash",
                next_model="gemini-3.6-flash",
                attempt=2,
                error=ANY,
            )

    @pytest.mark.asyncio
    async def test_process_chat_exhaustion_raises_503(
        self,
        mock_db_session: AsyncMock,
        mock_session_service: AsyncMock,
        mock_rag_orchestrator: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Cenário 4: Todas as 3 tentativas falham; deve levantar HTTPException 503 com limite estrito."""
        primary_llm = _create_mock_chat_model("gemini-3.8-flash")
        primary_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Falha 1"))

        fb1_llm = _create_mock_chat_model("gemini-3.7-flash")
        fb1_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Falha 2"))

        fb2_llm = _create_mock_chat_model("gemini-3.6-flash")
        fb2_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Falha 3"))

        chat_service = ChatService(
            session=mock_db_session,
            llm=primary_llm,
            fallback_llms=[fb1_llm, fb2_llm],
            rag_orchestrator=mock_rag_orchestrator,
            session_service=mock_session_service,
            settings=test_settings,
        )

        req = ChatRequest(session_id=uuid4(), message="Qual a norma?")

        with patch("lumi.services.chat_service.logger.warning") as mock_warn:
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.process_chat(req)

            assert exc_info.value.status_code == 503
            assert "sobrecarregado" in exc_info.value.detail.lower()

            assert primary_llm.ainvoke.call_count == 1
            assert fb1_llm.ainvoke.call_count == 1
            assert fb2_llm.ainvoke.call_count == 1
            assert mock_warn.call_count == 2


class TestChatServiceStreamFallback:
    """Testes de fallback automático para streaming SSE (stream_chat)."""

    @pytest.mark.asyncio
    async def test_stream_chat_fallback_to_3_7_on_immediate_failure(
        self,
        mock_db_session: AsyncMock,
        mock_session_service: AsyncMock,
        mock_rag_orchestrator: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Fallback no streaming quando o modelo primário falha antes de enviar tokens."""
        primary_llm = _create_mock_chat_model("gemini-3.8-flash")

        async def _failing_stream(
            *args: Any, **kwargs: Any
        ) -> AsyncGenerator[AIMessageChunk, None]:
            raise RuntimeError("503 Service Unavailable")
            yield  # pragma: no cover

        primary_llm.astream = _failing_stream

        fb1_llm = _create_mock_chat_model("gemini-3.7-flash")

        async def _success_stream(
            *args: Any, **kwargs: Any
        ) -> AsyncGenerator[AIMessageChunk, None]:
            for t in ["Texto ", "transmitido ", "pelo 3.7."]:
                yield AIMessageChunk(content=t)

        fb1_llm.astream = _success_stream

        fb2_llm = _create_mock_chat_model("gemini-3.6-flash")
        fb2_llm.astream = AsyncMock()

        chat_service = ChatService(
            session=mock_db_session,
            llm=primary_llm,
            fallback_llms=[fb1_llm, fb2_llm],
            rag_orchestrator=mock_rag_orchestrator,
            session_service=mock_session_service,
            settings=test_settings,
        )

        req = ChatRequest(session_id=uuid4(), message="Dúvida streaming", stream=True)

        with patch("lumi.services.chat_service.logger.warning") as mock_warn:
            events = [event async for event in chat_service.stream_chat(req)]

            assert any("Texto" in ev for ev in events)
            assert any("pelo 3.7." in ev for ev in events)
            mock_warn.assert_called_once_with(
                "llm_fallback_attempt",
                failed_model="gemini-3.8-flash",
                next_model="gemini-3.7-flash",
                attempt=1,
                error=ANY,
            )

    @pytest.mark.asyncio
    async def test_stream_chat_exhaustion_raises_503(
        self,
        mock_db_session: AsyncMock,
        mock_session_service: AsyncMock,
        mock_rag_orchestrator: AsyncMock,
        test_settings: Settings,
    ) -> None:
        """Esgotamento de 3 tentativas antes de emitir tokens levanta HTTPException 503."""
        primary_llm = _create_mock_chat_model("gemini-3.8-flash")

        async def _fail1(*args: Any, **kwargs: Any) -> AsyncGenerator[AIMessageChunk, None]:
            raise RuntimeError("Falha 1")
            yield  # pragma: no cover

        primary_llm.astream = _fail1

        fb1_llm = _create_mock_chat_model("gemini-3.7-flash")

        async def _fail2(*args: Any, **kwargs: Any) -> AsyncGenerator[AIMessageChunk, None]:
            raise RuntimeError("Falha 2")
            yield  # pragma: no cover

        fb1_llm.astream = _fail2

        fb2_llm = _create_mock_chat_model("gemini-3.6-flash")

        async def _fail3(*args: Any, **kwargs: Any) -> AsyncGenerator[AIMessageChunk, None]:
            raise RuntimeError("Falha 3")
            yield  # pragma: no cover

        fb2_llm.astream = _fail3

        chat_service = ChatService(
            session=mock_db_session,
            llm=primary_llm,
            fallback_llms=[fb1_llm, fb2_llm],
            rag_orchestrator=mock_rag_orchestrator,
            session_service=mock_session_service,
            settings=test_settings,
        )

        req = ChatRequest(session_id=uuid4(), message="Dúvida", stream=True)

        with patch("lumi.services.chat_service.logger.warning") as mock_warn:
            with pytest.raises(HTTPException) as exc_info:
                async for _ in chat_service.stream_chat(req):
                    pass

            assert exc_info.value.status_code == 503
            assert mock_warn.call_count == 2


class TestQueryRewriterFallback:
    """Testes de fallback automático para reescrita de queries (QueryRewriter.rewrite)."""

    @pytest.mark.asyncio
    async def test_rewriter_fallback_to_3_7(self, test_settings: Settings) -> None:
        """Reescritor recupera no 1º fallback quando modelo 3.8 falha."""
        primary_llm = _create_mock_chat_model("gemini-3.8-flash")
        primary_llm.ainvoke = AsyncMock(side_effect=RuntimeError("503 Service Unavailable"))

        fb1_llm = _create_mock_chat_model("gemini-3.7-flash")
        fb1_llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Qual a especificação para ramal subterrâneo?")
        )

        fb2_llm = _create_mock_chat_model("gemini-3.6-flash")
        fb2_llm.ainvoke = AsyncMock()

        rewriter = QueryRewriter(
            llm=primary_llm,
            fallback_llms=[fb1_llm, fb2_llm],
            settings=test_settings,
        )

        history = [HumanMessage(content="Falávamos sobre ramais prediais.")]
        query = "E no subterrâneo?"

        with patch("lumi.rag.rewriter.logger.warning") as mock_warn:
            result = await rewriter.rewrite(query=query, chat_history=history)

            assert result == "Qual a especificação para ramal subterrâneo?"
            primary_llm.ainvoke.assert_called_once()
            fb1_llm.ainvoke.assert_called_once()
            fb2_llm.ainvoke.assert_not_called()
            mock_warn.assert_called_once_with(
                "llm_fallback_attempt",
                failed_model="gemini-3.8-flash",
                next_model="gemini-3.7-flash",
                attempt=1,
                error=ANY,
            )

    @pytest.mark.asyncio
    async def test_rewriter_all_fail_falls_back_to_original_query(
        self, test_settings: Settings
    ) -> None:
        """Quando todas as tentativas da cadeia falharem, o reescritor retorna a query original."""
        primary_llm = _create_mock_chat_model("gemini-3.8-flash")
        primary_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Falha 1"))

        fb1_llm = _create_mock_chat_model("gemini-3.7-flash")
        fb1_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Falha 2"))

        fb2_llm = _create_mock_chat_model("gemini-3.6-flash")
        fb2_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Falha 3"))

        rewriter = QueryRewriter(
            llm=primary_llm,
            fallback_llms=[fb1_llm, fb2_llm],
            settings=test_settings,
        )

        history = [HumanMessage(content="Falávamos sobre ramais prediais.")]
        query = "E no subterrâneo?"

        with patch("lumi.rag.rewriter.logger.warning") as mock_warn:
            result = await rewriter.rewrite(query=query, chat_history=history)

            assert result == query
            assert primary_llm.ainvoke.call_count == 1
            assert fb1_llm.ainvoke.call_count == 1
            assert fb2_llm.ainvoke.call_count == 1
            # 2 avisos de transição + 1 aviso de fallback geral na falha
            assert mock_warn.call_count == 3
