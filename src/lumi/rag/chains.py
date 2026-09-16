"""Orquestrador de contexto RAG: reescrita contextual, recuperação vetorial e reranking."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from lumi.rag.retriever import RetrievalResult

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage

    from lumi.rag.reranker import NormativeReranker
    from lumi.rag.retriever import NormativeRetriever
    from lumi.rag.rewriter import QueryRewriter

logger = structlog.get_logger(__name__)


class RagContextOrchestrator:
    """Orquestra a cadeia de contexto normativo: reescrita -> retriever -> reranker."""

    def __init__(
        self,
        retriever: NormativeRetriever,
        rewriter: QueryRewriter | None = None,
        reranker: NormativeReranker | None = None,
    ) -> None:
        """Inicializa o orquestrador com o retriever obrigatório e componentes opcionais."""
        self.retriever = retriever
        self.rewriter = rewriter
        self.reranker = reranker

    async def get_context(
        self,
        query: str,
        chat_history: list[BaseMessage] | None = None,
        document_code: str | None = None,
    ) -> RetrievalResult:
        """Executa a pipeline integrada de contextualização para perguntas da Lumi.

        Fluxo de execução:
        1. Se houver rewriter configurado, reescreve a query com base no chat_history.
        2. Executa a busca vetorial através do NormativeRetriever.
        3. Curto-circuito defensivo: se o retriever disparar contingência (ex.: threshold
           não atingido ou pergunta vazia), encerra o fluxo sem acionar o reranker.
        4. Se houver reranker configurado, refina os fragmentos candidatos listwise.
        5. Retorna o RetrievalResult consolidado.

        Args:
            query: Pergunta bruta do usuário.
            chat_history: Histórico opcional de mensagens prévias.
            document_code: Filtro opcional por código de norma técnica (ex.: 'DIS-NOR-030').

        Returns:
            RetrievalResult: Resultado final com chunks selecionados ou contingência.
        """
        # 1. Reescrita contextual
        if self.rewriter is not None:
            effective_query = await self.rewriter.rewrite(query=query, chat_history=chat_history)
        else:
            effective_query = query.strip() if query else ""

        logger.debug(
            "rag_orchestrator_query_prepared",
            original_query=query,
            effective_query=effective_query,
            has_history=bool(chat_history),
            document_code=document_code,
        )

        # 2. Recuperação vetorial
        retrieval_res = await self.retriever.retrieve(
            query=effective_query,
            document_code=document_code,
        )

        # 3. Curto-circuito defensivo em contingência
        if retrieval_res.is_contingency:
            logger.info(
                "rag_orchestrator_contingency_short_circuit",
                query=effective_query,
                contingency_message=retrieval_res.contingency_message,
            )
            return retrieval_res

        # 4. Reranking semântico listwise
        if self.reranker is not None and retrieval_res.chunks:
            reranked_chunks = await self.reranker.rerank(
                query=effective_query,
                chunks=retrieval_res.chunks,
            )
            return RetrievalResult(
                query=effective_query,
                chunks=reranked_chunks,
                is_contingency=False,
                contingency_message=None,
            )

        return retrieval_res
