"""Módulo de recuperação semântica vetorial, guardrails de similaridade e contingência."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog

from lumi.core.config import Settings, get_settings
from lumi.db.vector_store import NormativeVectorStore
from lumi.rag.llm_factory import get_embeddings
from lumi.rag.prompts import CONTINGENCY_NO_SOURCES_MESSAGE
from lumi.schemas.chat import SourceMetadata

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass
class RetrievedChunk:
    """Representa um fragmento normativo recuperado do banco vetorial."""

    chunk_id: UUID
    document_code: str
    document_title: str
    revision: str
    section_code: str | None
    section_title: str | None
    page_number: int | None
    content: str
    similarity_score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_source_metadata(self) -> SourceMetadata:
        """Converte o fragmento recuperado para o contrato SourceMetadata da API."""
        section = self.section_code or self.section_title or "Geral"
        page = self.page_number if (self.page_number is not None and self.page_number >= 1) else 1
        score = max(0.0, min(1.0, float(self.similarity_score)))
        return SourceMetadata(
            document_code=self.document_code or "NORMA",
            revision=self.revision or "",
            section=section,
            page=page,
            relevance_score=score,
            snippet=self.content,
        )


@dataclass
class RetrievalResult:
    """Resultado consolidado da recuperação vetorial com suporte a contingência."""

    query: str
    chunks: list[RetrievedChunk]
    is_contingency: bool
    contingency_message: str | None = None

    @property
    def sources(self) -> list[SourceMetadata]:
        """Retorna os metadados de fontes para serialização na API e eventos SSE."""
        if self.is_contingency or not self.chunks:
            return []
        return [chunk.to_source_metadata() for chunk in self.chunks]

    @property
    def formatted_context(self) -> str:
        """Gera o bloco textual de contexto formatado para injeção no prompt mestre RAG.

        Formato padronizado:
        [Fonte: {document_code}, Item {section_code}, Pág. {page_number}]
        {content}
        """
        if self.is_contingency or not self.chunks:
            return ""

        blocks: list[str] = []
        for chunk in self.chunks:
            sec = chunk.section_code or chunk.section_title or "Geral"
            pag = chunk.page_number if chunk.page_number is not None else "N/A"
            header = f"[Fonte: {chunk.document_code}, Item {sec}, Pág. {pag}]"
            blocks.append(f"{header}\n{chunk.content}")

        return "\n\n".join(blocks)


class NormativeRetriever:
    """Orquestrador de recuperação vetorial, aplicação de threshold e salvaguardas."""

    def __init__(
        self,
        session: AsyncSession | None = None,
        vector_store: NormativeVectorStore | None = None,
        embeddings: Embeddings | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Inicializa o componente de recuperação com dependências injetadas ou resolvidas."""
        self.settings = settings or get_settings()
        self.session = session

        if vector_store is not None:
            self.vector_store: NormativeVectorStore | None = vector_store
        elif session is not None:
            self.vector_store = NormativeVectorStore(session=session)
        else:
            self.vector_store = None

        self.embeddings = embeddings or get_embeddings(settings=self.settings)

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
        document_code: str | None = None,
    ) -> RetrievalResult:
        """Executa a recuperação vetorial de chunks normativos aplicando threshold de similaridade.

        Caso a query seja vazia ou nenhum fragmento alcance o threshold mínimo configurado,
        retorna imediatamente uma resposta de contingência determinística
        (CONTINGENCY_NO_SOURCES_MESSAGE), dispensando a chamada à LLM.

        Args:
            query: Pergunta ou texto de busca enviado pelo usuário.
            top_k: Quantidade máxima de fragmentos a recuperar (padrão derivado de
              settings).
            threshold: Limiar mínimo de similaridade de cosseno (padrão derivado de
              settings).
            document_code: Filtro opcional por código da norma técnica (ex.:
              'DIS-NOR-030').

        Returns:
            RetrievalResult: Resultado com chunks válidos ou estado de contingência
            acionado.
        """
        stripped_query = query.strip() if query else ""
        if not stripped_query:
            logger.info(
                "retrieval_empty_query_contingency",
                query=query,
            )
            return RetrievalResult(
                query=query,
                chunks=[],
                is_contingency=True,
                contingency_message=CONTINGENCY_NO_SOURCES_MESSAGE,
            )

        if self.vector_store is None:
            if self.session is not None:
                self.vector_store = NormativeVectorStore(self.session)
            else:
                raise RuntimeError(
                    "NormativeVectorStore ou AsyncSession é obrigatório para execução do retriever."
                )

        effective_top_k = top_k if top_k is not None else self.settings.top_k_retrieval
        effective_threshold = (
            threshold if threshold is not None else self.settings.similarity_threshold
        )

        logger.debug(
            "retrieval_query_started",
            query=stripped_query,
            top_k=effective_top_k,
            threshold=effective_threshold,
            document_code=document_code,
        )

        # 1. Gera embedding da query (suporta métodos assíncronos e síncronos)
        if hasattr(self.embeddings, "aembed_query"):
            res = self.embeddings.aembed_query(query)
            if inspect.isawaitable(res):
                query_vector = await res
            else:
                query_vector = res
        else:
            query_vector = self.embeddings.embed_query(query)

        # 2. Busca chunks similares no pgvector via NormativeVectorStore
        similar_rows = await self.vector_store.search_similar(
            query_embedding=query_vector,
            top_k=effective_top_k,
            threshold=effective_threshold,
            document_code=document_code,
        )

        # 3. Converte entidades do banco para RetrievedChunk e aplica filtro defensivo de threshold
        retrieved_chunks: list[RetrievedChunk] = []
        for chunk_entity, score in similar_rows:
            if score < effective_threshold:
                continue

            doc = getattr(chunk_entity, "document", None)
            doc_code = (
                doc.code
                if doc and hasattr(doc, "code")
                else (getattr(chunk_entity, "document_code", "") or "")
            )
            doc_title = (
                doc.title
                if doc and hasattr(doc, "title")
                else (getattr(chunk_entity, "document_title", "") or "")
            )
            rev = (doc.revision if doc and hasattr(doc, "revision") and doc.revision else "") or (
                getattr(chunk_entity, "revision", "") or ""
            )

            retrieved_chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_entity.id,
                    document_code=doc_code,
                    document_title=doc_title,
                    revision=rev,
                    section_code=chunk_entity.section_code,
                    section_title=chunk_entity.section_title,
                    page_number=chunk_entity.page_number,
                    content=chunk_entity.content,
                    similarity_score=float(score),
                    metadata=getattr(chunk_entity, "metadata_", {}) or {},
                )
            )

        # 4. Avalia contingência
        if not retrieved_chunks:
            logger.info(
                "retrieval_contingency_triggered",
                query=query,
                threshold=effective_threshold,
                reason="no_chunks_above_threshold",
            )
            return RetrievalResult(
                query=query,
                chunks=[],
                is_contingency=True,
                contingency_message=CONTINGENCY_NO_SOURCES_MESSAGE,
            )

        logger.info(
            "retrieval_query_success",
            query=query,
            chunks_count=len(retrieved_chunks),
            top_score=retrieved_chunks[0].similarity_score,
            lowest_score=retrieved_chunks[-1].similarity_score,
        )

        return RetrievalResult(
            query=query,
            chunks=retrieved_chunks,
            is_contingency=False,
            contingency_message=None,
        )
