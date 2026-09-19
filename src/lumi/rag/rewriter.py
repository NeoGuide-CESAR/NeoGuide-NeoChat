"""Módulo de reescrita contextual de queries multi-turn para busca vetorial RAG."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from lumi.core.config import Settings, get_settings
from lumi.rag.llm_factory import (
    MAX_FALLBACK_ATTEMPTS,
    get_llm_chain,
    get_model_name,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = structlog.get_logger(__name__)

REWRITER_SYSTEM_PROMPT: str = """Você é um assistente técnico especializado em normas da Neoenergia Pernambuco (DIS-NOR-030 e DIS-NOR-053).
Sua missão é converter a pergunta mais recente do usuário em uma consulta de busca autônoma, técnica e completa, considerando o histórico de conversa.

Diretrizes estritas:
1. Desambigue pronomes anafóricos e referências elípticas (ex.: 'dele', 'esse caso', 'e para 40 apartamentos?'), explicitando o contexto técnico discutido anteriormente.
2. Preserve e inclua menções a códigos normativos pertinentes (DIS-NOR-030, DIS-NOR-053) e jargões da engenharia elétrica (demanda, ramal de ligação, medição agrupada, queda de tensão).
3. NUNCA responda à dúvida do usuário. Gere exclusivamente a consulta reformulada.
4. NÃO inclua saudações, preâmbulos, explicações ou blocos de código. Retorne apenas o texto da consulta reescrita.
"""


class QueryRewriter:
    """Componente responsável pela reformulação contextual de perguntas em diálogos multi-turn."""

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        fallback_llms: list[BaseChatModel] | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Inicializa o reescritor com modelo de linguagem e configurações do sistema."""
        self.settings = settings or get_settings()
        self._llm = llm
        self._fallback_llms = fallback_llms
        self._models: list[BaseChatModel] | None = None

    @property
    def models(self) -> list[BaseChatModel]:
        """Obtém ou inicializa tardiamente a cadeia ordenada de modelos para reescrita."""
        if self._models is None:
            if self._llm is not None:
                chain = [self._llm]
                if self._fallback_llms:
                    chain.extend(self._fallback_llms)
                self._models = chain
            else:
                self._models = get_llm_chain(settings=self.settings)
        return self._models

    @property
    def llm(self) -> BaseChatModel:
        """Obtém o modelo primário configurado."""
        return self.models[0]

    @llm.setter
    def llm(self, value: BaseChatModel) -> None:
        """Define o modelo primário configurado."""
        self._llm = value
        self._models = None

    async def rewrite(
        self,
        query: str,
        chat_history: list[BaseMessage] | None = None,
    ) -> str:
        """Reescreve a pergunta do usuário contextualizando-a com o histórico da conversa.

        Caso o histórico esteja vazio (primeiro turno), a query seja vazia ou a funcionalidade
        esteja desabilitada via configurações, realiza bypass imediato sem invocar a LLM.
        Em caso de erro na chamada da LLM, aplica fallback gracioso para a query original.

        Args:
            query: Pergunta bruta enviada pelo usuário.
            chat_history: Lista opcional de mensagens anteriores da sessão (HumanMessage/AIMessage).

        Returns:
            str: Pergunta reescrita e contextualizada, ou a query original limpa em caso de bypass/fallback.
        """
        stripped_query = query.strip() if query else ""
        if not stripped_query:
            logger.debug("query_rewriter_bypass_empty_query")
            return stripped_query

        # Bypass se desabilitado por configuração ou se não há histórico prévio (1º turno)
        if not self.settings.query_rewriter_enabled or not chat_history:
            logger.debug(
                "query_rewriter_bypass",
                enabled=self.settings.query_rewriter_enabled,
                has_history=bool(chat_history),
                query=stripped_query,
            )
            return stripped_query

        logger.debug(
            "query_rewriter_started",
            query=stripped_query,
            history_length=len(chat_history),
        )

        messages: list[BaseMessage] = [
            SystemMessage(content=REWRITER_SYSTEM_PROMPT),
            *chat_history,
            HumanMessage(content=f"Pergunta a reformular: {stripped_query}"),
        ]

        models = self.models
        max_attempts = min(len(models), MAX_FALLBACK_ATTEMPTS)

        for attempt_idx in range(max_attempts):
            attempt = attempt_idx + 1
            current_model = models[attempt_idx]
            current_model_name = get_model_name(current_model)

            try:
                response = await current_model.ainvoke(messages)
                content = str(response.content).strip()
                # Limpa aspas ou delimitadores que a LLM possa gerar
                cleaned_query = content.strip("\"'").strip()

                if not cleaned_query:
                    logger.warning(
                        "query_rewriter_empty_response_fallback",
                        original_query=stripped_query,
                    )
                    return stripped_query

                logger.info(
                    "query_rewriter_success",
                    original_query=stripped_query,
                    rewritten_query=cleaned_query,
                )
                return cleaned_query

            except Exception as exc:
                if attempt < max_attempts:
                    next_model_name = get_model_name(models[attempt_idx + 1])
                    logger.warning(
                        "llm_fallback_attempt",
                        failed_model=current_model_name,
                        next_model=next_model_name,
                        attempt=attempt,
                        error=str(exc),
                    )
                    continue

                logger.warning(
                    "query_rewriter_fallback_on_error",
                    query=stripped_query,
                    error=str(exc),
                    exc_info=True,
                )
                return stripped_query

        return stripped_query
