"""Serviço para persistência analítica e desacoplamento assíncrono de interações conversacionais."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lumi.db.models import ChatMessage, ChatSession, NormativeQueryAnalytics
from lumi.db.session import get_db_session
from lumi.rag.output_guardrails import extract_citations, validate_output

if TYPE_CHECKING:
    from lumi.rag.retriever import RetrievedChunk

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """Serviço de registro e auditoria de métricas analíticas na tabela normative_query_analytics."""

    def __init__(self, session: AsyncSession) -> None:
        """Inicializa o serviço analítico vinculado a uma sessão do SQLAlchemy."""
        self.session = session

    async def record_query_analytics(
        self,
        query_text: str,
        latency_ms: int,
        session_id: uuid.UUID | None = None,
        top_document_code: str | None = None,
        top_similarity_score: float | None = None,
    ) -> NormativeQueryAnalytics:
        """Registra telemetria de uma consulta normativa individual."""
        record = NormativeQueryAnalytics(
            id=uuid.uuid4(),
            session_id=session_id,
            query_text=query_text,
            top_document_code=top_document_code,
            top_similarity_score=top_similarity_score,
            latency_ms=latency_ms,
            created_at=datetime.now(UTC),
        )
        self.session.add(record)
        await self.session.flush()
        return record


async def persist_interaction_background(
    session_id: uuid.UUID,
    query_text: str,
    assistant_message: str,
    sources: list[dict[str, Any]] | None = None,
    top_document_code: str | None = None,
    top_similarity_score: float | None = None,
    latency_ms: int = 0,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    max_retries: int = 1,
    retry_backoff_seconds: float = 0.5,
    retrieved_chunks: list[RetrievedChunk] | list[dict[str, Any]] | None = None,
) -> bool:
    """Executa a persistência da mensagem do assistente e telemetria analítica em segundo plano.

    Características:
    - Executa validação assíncrona não-bloqueante de guardrails de saída (citações e cálculo).
    - Emite alerta estruturado no structlog caso detecte violações ou alucinações.
    - Abre sessão assíncrona independente através de `get_db_session(session_factory=...)`.
    - Atualiza `ChatSession.updated_at` e insere `ChatMessage` com `role='assistant'` e audit_flags.
    - Insere telemetria em `NormativeQueryAnalytics`.
    - Tolerância a falhas: até `max_retries` retentativas com `retry_backoff_seconds` de espera.
    - Captura e loga exceções via `structlog` sem propagar erro ao cliente.

    Returns:
        bool: True se a persistência for concluída com sucesso; False em caso de falha após retentativas.
    """
    # 1. Executa validação assíncrona não-bloqueante de guardrails de saída
    guardrail_result = validate_output(
        response_text=assistant_message,
        retrieved_chunks=retrieved_chunks if retrieved_chunks is not None else (sources or []),
    )

    if not guardrail_result.is_valid:
        logger.warning(
            "output_guardrail_violation",
            session_id=str(session_id),
            warning_flags=guardrail_result.warning_flags,
            hallucinated_citations=guardrail_result.hallucinated_citations,
            has_calculation_violation=guardrail_result.has_calculation_violation,
        )

    # 2. Prepara fontes persistidas enriquecidas com audit_flags se houver inconformidades
    persisted_sources: list[dict[str, Any]] = []
    if sources:
        for s in sources:
            src_dict = dict(s)
            if guardrail_result.warning_flags:
                src_dict["audit_flags"] = guardrail_result.warning_flags
            persisted_sources.append(src_dict)
    elif guardrail_result.hallucinated_citations:
        # Registra citações alucinadas como metadados estruturados para auditoria
        for hal in guardrail_result.hallucinated_citations:
            cites = extract_citations(hal)
            doc = cites[0][0] if cites else "AUDIT"
            sec = cites[0][1] if cites else "Item Inválido"
            persisted_sources.append({
                "document_code": doc,
                "revision": "",
                "section": sec or "Geral",
                "page": 1,
                "relevance_score": 0.0,
                "snippet": hal,
                "audit_flags": guardrail_result.warning_flags,
            })

    total_attempts = 1 + max_retries
    attempts = 0

    while attempts < total_attempts:
        attempts += 1
        try:
            async with get_db_session(session_factory=session_factory) as session:
                now = datetime.now(UTC)

                # Atualiza o timestamp da sessão vinculada, se existente
                result = await session.execute(
                    select(ChatSession).where(ChatSession.id == session_id)
                )
                chat_session = result.scalar_one_or_none()
                if chat_session is not None:
                    chat_session.updated_at = now

                # Persiste a mensagem do assistente
                msg = ChatMessage(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    role="assistant",
                    content=assistant_message,
                    sources=persisted_sources,
                    created_at=now,
                )
                session.add(msg)

                # Persiste telemetria analítica
                analytics_service = AnalyticsService(session=session)
                await analytics_service.record_query_analytics(
                    session_id=session_id,
                    query_text=query_text,
                    latency_ms=latency_ms,
                    top_document_code=top_document_code,
                    top_similarity_score=top_similarity_score,
                )

            logger.info(
                "persist_interaction_background_success",
                session_id=str(session_id),
                latency_ms=latency_ms,
                top_doc=top_document_code,
                attempts=attempts,
            )
            return True

        except Exception as exc:
            if attempts < total_attempts:
                logger.warning(
                    "persist_interaction_background_retry",
                    session_id=str(session_id),
                    attempt=attempts,
                    error=str(exc),
                )
                await asyncio.sleep(retry_backoff_seconds)
            else:
                logger.error(
                    "persist_interaction_background_failed",
                    session_id=str(session_id),
                    attempt=attempts,
                    error=str(exc),
                    exc_info=True,
                )
                return False

    return False
