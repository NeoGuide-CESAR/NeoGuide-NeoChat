"""Serviço de orquestração do chat Lumi: streaming SSE, fallback síncrono e RAG."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.core.config import Settings, get_settings
from lumi.rag.chains import RagContextOrchestrator
from lumi.rag.guardrails import validate_input
from lumi.rag.llm_factory import get_llm
from lumi.rag.prompts import CONTINGENCY_NO_SOURCES_MESSAGE, get_rag_prompt_template
from lumi.rag.reranker import NormativeReranker
from lumi.rag.retriever import NormativeRetriever
from lumi.rag.rewriter import QueryRewriter
from lumi.schemas.chat import (
    ChatRequest,
    ChatResponse,
    StreamDoneEvent,
    StreamErrorEvent,
    StreamSourcesEvent,
    StreamTokenEvent,
)
from lumi.services.session_service import (
    SessionService,
)

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

logger = structlog.get_logger(__name__)


def create_rag_orchestrator(
    session: AsyncSession,
    settings: Settings,
    llm: BaseChatModel,
) -> RagContextOrchestrator:
    """Cria a instância padrão de RagContextOrchestrator com retriever, rewriter e reranker."""
    retriever = NormativeRetriever(session=session, settings=settings)
    rewriter = (
        QueryRewriter(llm=llm, settings=settings)
        if settings.query_rewriter_enabled
        else None
    )
    reranker = (
        NormativeReranker(llm=llm, settings=settings)
        if settings.reranker_enabled
        else None
    )
    return RagContextOrchestrator(
        retriever=retriever,
        rewriter=rewriter,
        reranker=reranker,
    )


class ChatService:
    """Serviço de orquestração conversacional da Lumi com suporte a streaming SSE e modo síncrono."""

    def __init__(
        self,
        session: AsyncSession,
        llm: BaseChatModel | None = None,
        rag_orchestrator: RagContextOrchestrator | None = None,
        session_service: SessionService | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Inicializa o serviço de chat com injeção de dependências ou inicialização tardia."""
        self.session = session
        self.settings = settings or get_settings()
        self._llm = llm
        self._rag_orchestrator = rag_orchestrator
        self.session_service = session_service or SessionService(
            session=self.session,
            settings=self.settings,
        )

    @property
    def llm(self) -> BaseChatModel:
        """Obtém ou inicializa tardiamente o modelo LLM configurado com temperatura determinística."""
        if self._llm is None:
            self._llm = get_llm(temperature=0.0, settings=self.settings)
        return self._llm

    @property
    def rag_orchestrator(self) -> RagContextOrchestrator:
        """Obtém ou inicializa tardiamente o orquestrador RAG integrado."""
        if self._rag_orchestrator is None:
            self._rag_orchestrator = create_rag_orchestrator(
                session=self.session,
                settings=self.settings,
                llm=self.llm,
            )
        return self._rag_orchestrator

    @staticmethod
    def _format_sse(event_type: str, data: BaseModel) -> str:
        """Formata evento no padrão W3C Server-Sent Events (SSE)."""
        return f"event: {event_type}\ndata: {data.model_dump_json()}\n\n"

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Transmite a resposta conversacional em tempo real através de Server-Sent Events (SSE).

        Fluxo de execução:
        1. Validação de sessão ativa e TTL de inatividade (SessionNotFoundError / SessionExpiredError).
        2. Avaliação determinística de guardrails de entrada (PII, Prompt Injection e Escopo).
        3. Obtenção da janela de histórico multi-turn anterior à pergunta atual.
        4. Persistência da pergunta sanitizada do usuário.
        5. Recuperação contextual RAG (reescrita, busca vetorial e reranking).
        6. Resposta de contingência imediata caso não haja fontes suficientes.
        7. Geração streaming de tokens pela LLM com emissão progressiva de eventos token.
        8. Emissão de evento sources e done com encerramento e persistência transacional.
        """
        # 1. Validação de sessão ativa e expiração TTL
        await self.session_service.get_session_or_raise(request.session_id, check_ttl=True)

        # 2. Avaliação de guardrails de entrada
        guard_result = validate_input(request.message)
        if not guard_result.is_allowed:
            rejection_text = (
                guard_result.rejection_reason
                or "Solicitação recusada por diretrizes de segurança e escopo."
            )
            logger.info(
                "chat_service_guardrail_rejected",
                session_id=str(request.session_id),
                is_injection=guard_result.is_injection,
            )
            await self.session_service.add_message(
                request.session_id,
                role="user",
                content=guard_result.sanitized_text,
            )
            await self.session_service.add_message(
                request.session_id,
                role="assistant",
                content=rejection_text,
                sources=[],
            )
            yield self._format_sse("token", StreamTokenEvent(token=rejection_text))
            yield self._format_sse("sources", StreamSourcesEvent(sources=[]))
            yield self._format_sse("done", StreamDoneEvent(session_id=request.session_id))
            return

        # 3. Histórico multi-turn recente anterior à pergunta atual
        history_before_query = await self.session_service.get_langchain_messages(
            request.session_id,
            limit=self.settings.chat_history_limit,
        )

        # 4. Persistência da mensagem do usuário sanitizada
        await self.session_service.add_message(
            request.session_id,
            role="user",
            content=guard_result.sanitized_text,
        )

        # 5. Execução do pipeline RAG
        rag_result = await self.rag_orchestrator.get_context(
            query=guard_result.sanitized_text,
            chat_history=history_before_query,
        )

        # 6. Avaliação de contingência normativa
        if rag_result.is_contingency:
            contingency_text = (
                rag_result.contingency_message or CONTINGENCY_NO_SOURCES_MESSAGE
            )
            logger.info(
                "chat_service_contingency_triggered",
                session_id=str(request.session_id),
            )
            await self.session_service.add_message(
                request.session_id,
                role="assistant",
                content=contingency_text,
                sources=[],
            )
            yield self._format_sse("token", StreamTokenEvent(token=contingency_text))
            yield self._format_sse("sources", StreamSourcesEvent(sources=[]))
            yield self._format_sse("done", StreamDoneEvent(session_id=request.session_id))
            return

        # 7. Geração generativa streaming via LLM
        prompt_template = get_rag_prompt_template()
        prompt_messages = prompt_template.format_messages(
            context=rag_result.formatted_context,
            chat_history=history_before_query,
            question=guard_result.sanitized_text,
        )

        full_response = ""
        try:
            async for chunk in self.llm.astream(prompt_messages):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if isinstance(content, list):
                    token_str = "".join(
                        str(b.get("text", b) if isinstance(b, dict) else b)
                        for b in content
                    )
                else:
                    token_str = str(content)

                if token_str:
                    full_response += token_str
                    yield self._format_sse("token", StreamTokenEvent(token=token_str))

            yield self._format_sse("sources", StreamSourcesEvent(sources=rag_result.sources))
            yield self._format_sse("done", StreamDoneEvent(session_id=request.session_id))

            # Persiste resposta completa do assistente com fontes normativas associadas
            await self.session_service.add_message(
                request.session_id,
                role="assistant",
                content=full_response,
                sources=[s.model_dump() for s in rag_result.sources],
            )

        except Exception as exc:
            logger.error(
                "chat_service_llm_stream_error",
                session_id=str(request.session_id),
                error=str(exc),
                exc_info=True,
            )
            yield self._format_sse(
                "error",
                StreamErrorEvent(
                    error="Falha durante a geração da resposta pelo assistente.",
                    code="LLM_STREAM_ERROR",
                ),
            )

    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """Processa a mensagem de forma síncrona retornando payload consolidado ChatResponse."""
        # 1. Validação de sessão ativa e TTL
        await self.session_service.get_session_or_raise(request.session_id, check_ttl=True)

        # 2. Avaliação de guardrails de entrada
        guard_result = validate_input(request.message)
        if not guard_result.is_allowed:
            rejection_text = (
                guard_result.rejection_reason
                or "Solicitação recusada por diretrizes de segurança e escopo."
            )
            logger.info(
                "chat_service_sync_guardrail_rejected",
                session_id=str(request.session_id),
                is_injection=guard_result.is_injection,
            )
            await self.session_service.add_message(
                request.session_id,
                role="user",
                content=guard_result.sanitized_text,
            )
            await self.session_service.add_message(
                request.session_id,
                role="assistant",
                content=rejection_text,
                sources=[],
            )
            return ChatResponse(
                session_id=request.session_id,
                response=rejection_text,
                sources=[],
            )

        # 3. Histórico multi-turn recente anterior à pergunta
        history_before_query = await self.session_service.get_langchain_messages(
            request.session_id,
            limit=self.settings.chat_history_limit,
        )

        # 4. Persistência da pergunta sanitizada do usuário
        await self.session_service.add_message(
            request.session_id,
            role="user",
            content=guard_result.sanitized_text,
        )

        # 5. Execução do pipeline RAG
        rag_result = await self.rag_orchestrator.get_context(
            query=guard_result.sanitized_text,
            chat_history=history_before_query,
        )

        # 6. Avaliação de contingência normativa
        if rag_result.is_contingency:
            contingency_text = (
                rag_result.contingency_message or CONTINGENCY_NO_SOURCES_MESSAGE
            )
            await self.session_service.add_message(
                request.session_id,
                role="assistant",
                content=contingency_text,
                sources=[],
            )
            return ChatResponse(
                session_id=request.session_id,
                response=contingency_text,
                sources=[],
            )

        # 7. Invocação síncrona do LLM
        prompt_template = get_rag_prompt_template()
        prompt_messages = prompt_template.format_messages(
            context=rag_result.formatted_context,
            chat_history=history_before_query,
            question=guard_result.sanitized_text,
        )

        llm_response = await self.llm.ainvoke(prompt_messages)
        response_content = (
            llm_response.content
            if hasattr(llm_response, "content")
            else str(llm_response)
        )
        if isinstance(response_content, list):
            response_text = "".join(
                str(b.get("text", b) if isinstance(b, dict) else b)
                for b in response_content
            )
        else:
            response_text = str(response_content)

        await self.session_service.add_message(
            request.session_id,
            role="assistant",
            content=response_text,
            sources=[s.model_dump() for s in rag_result.sources],
        )

        return ChatResponse(
            session_id=request.session_id,
            response=response_text,
            sources=rag_result.sources,
        )
