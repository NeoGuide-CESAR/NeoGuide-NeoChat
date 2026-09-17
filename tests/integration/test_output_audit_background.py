"""Testes de integração para validação de guardrails de saída e auditoria em background."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.api.deps import get_db, get_db_session
from lumi.core.config import get_settings
from lumi.db.models import ChatMessage, ChatSession
from lumi.main import app
from lumi.rag.chains import RagContextOrchestrator
from lumi.rag.retriever import RetrievalResult, RetrievedChunk
from lumi.services.analytics_service import persist_interaction_background


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock da sessão do banco de dados para injeção no FastAPI."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture(autouse=True)
def override_db_dependency(mock_db: AsyncMock) -> Any:
    """Sobrescreve a dependência de banco de dados no FastAPI para todos os testes."""

    async def _override() -> Any:
        yield mock_db

    app.dependency_overrides[get_db] = _override
    app.dependency_overrides[get_db_session] = _override
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_db_session, None)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Headers contendo X-API-Key válida."""
    settings = get_settings()
    return {"X-API-Key": settings.api_key}


@pytest.fixture
def mock_retrieved_chunk() -> RetrievedChunk:
    """Fixture com fragmento normativo legítimo da DIS-NOR-030."""
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_code="DIS-NOR-030",
        document_title="Norma Técnica de Distribuição",
        revision="REV07",
        section_code="Item 5.2",
        section_title="Queda de Tensão",
        page_number=14,
        content="A queda de tensão máxima admissível é de 5%.",
        similarity_score=0.92,
        metadata={},
    )


class TestOutputAuditBackgroundIntegration:
    """Valida a execução assíncrona dos guardrails de saída via persist_interaction_background."""

    @pytest.mark.asyncio
    async def test_background_persistence_clean_response_no_warning(
        self,
        mock_retrieved_chunk: RetrievedChunk,
    ) -> None:
        """Resposta com citações legítimas e sem violação de cálculo não deve emitir warning."""
        session_id = uuid4()
        now = datetime.now(UTC)
        mock_session_obj = ChatSession(id=session_id, created_at=now, updated_at=now)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session_obj
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        sources = [
            {
                "document_code": "DIS-NOR-030",
                "page": 14,
                "section": "Item 5.2",
                "relevance_score": 0.92,
            }
        ]

        with (
            patch("lumi.services.analytics_service.get_db_session") as mock_get_db,
            patch("lumi.services.analytics_service.logger") as mock_logger,
        ):
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_db
            mock_cm.__aexit__.return_value = None
            mock_get_db.return_value = mock_cm

            success = await persist_interaction_background(
                session_id=session_id,
                query_text="Qual a queda máxima admissível?",
                assistant_message="O limite é de 5% [Fonte: DIS-NOR-030, Item 5.2].",
                sources=sources,
                top_document_code="DIS-NOR-030",
                top_similarity_score=0.92,
                latency_ms=300,
                retrieved_chunks=[mock_retrieved_chunk],
            )

        assert success is True
        # logger.warning não deve ter sido chamado para violações de guardrail
        mock_logger.warning.assert_not_called()

        added_items = [call.args[0] for call in mock_db.add.call_args_list]
        msg = next(item for item in added_items if isinstance(item, ChatMessage))
        assert msg.sources is not None
        assert len(msg.sources) == 1
        # Não deve haver flags de violação anexadas
        assert "audit_flags" not in msg.sources[0]

    @pytest.mark.asyncio
    async def test_background_persistence_detects_hallucination_and_logs_warning(
        self,
        mock_retrieved_chunk: RetrievedChunk,
    ) -> None:
        """Citação com item alucinado deve emitir logger.warning e persistir audit_flags."""
        session_id = uuid4()
        now = datetime.now(UTC)
        mock_session_obj = ChatSession(id=session_id, created_at=now, updated_at=now)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session_obj
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        sources = [
            {
                "document_code": "DIS-NOR-030",
                "page": 14,
                "section": "Item 5.2",
                "relevance_score": 0.92,
            }
        ]

        with (
            patch("lumi.services.analytics_service.get_db_session") as mock_get_db,
            patch("lumi.services.analytics_service.logger") as mock_logger,
        ):
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_db
            mock_cm.__aexit__.return_value = None
            mock_get_db.return_value = mock_cm

            # Mensagem cita Item 99.4 que não existe nos chunks
            success = await persist_interaction_background(
                session_id=session_id,
                query_text="Qual o item aplicável?",
                assistant_message="Consulte a regra no [Fonte: DIS-NOR-030, Item 99.4].",
                sources=sources,
                top_document_code="DIS-NOR-030",
                top_similarity_score=0.92,
                latency_ms=250,
                retrieved_chunks=[mock_retrieved_chunk],
            )

        assert success is True
        # logger.warning deve ter sido acionado com a flag HALLUCINATED_CITATION
        mock_logger.warning.assert_called_once()
        log_kwargs = mock_logger.warning.call_args.kwargs
        assert mock_logger.warning.call_args.args[0] == "output_guardrail_violation"
        assert "HALLUCINATED_CITATION" in log_kwargs["warning_flags"]
        assert any("99.4" in h for h in log_kwargs["hallucinated_citations"])

        # Metadados persistidos devem conter as flags de auditoria
        added_items = [call.args[0] for call in mock_db.add.call_args_list]
        msg = next(item for item in added_items if isinstance(item, ChatMessage))
        assert msg.sources is not None
        assert "HALLUCINATED_CITATION" in msg.sources[0].get("audit_flags", [])

    @pytest.mark.asyncio
    async def test_background_persistence_detects_calculation_violation_and_logs_warning(
        self,
        mock_retrieved_chunk: RetrievedChunk,
    ) -> None:
        """Cálculo absoluto sem direcionamento ao Wizard NeoGuide deve emitir warning e gravar flag."""
        session_id = uuid4()
        now = datetime.now(UTC)
        mock_session_obj = ChatSession(id=session_id, created_at=now, updated_at=now)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session_obj
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        sources = [
            {
                "document_code": "DIS-NOR-030",
                "page": 14,
                "section": "Item 5.2",
                "relevance_score": 0.92,
            }
        ]

        with (
            patch("lumi.services.analytics_service.get_db_session") as mock_get_db,
            patch("lumi.services.analytics_service.logger") as mock_logger,
        ):
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_db
            mock_cm.__aexit__.return_value = None
            mock_get_db.return_value = mock_cm

            # Mensagem fornece cálculo absoluto de demanda sem citar o Wizard NeoGuide
            success = await persist_interaction_background(
                session_id=session_id,
                query_text="Calcule a demanda do meu prédio",
                assistant_message=(
                    "A demanda do seu prédio é de exatos 142,5 kVA [Fonte: DIS-NOR-030, Item 5.2]."
                ),
                sources=sources,
                top_document_code="DIS-NOR-030",
                top_similarity_score=0.92,
                latency_ms=280,
                retrieved_chunks=[mock_retrieved_chunk],
            )

        assert success is True
        mock_logger.warning.assert_called_once()
        log_kwargs = mock_logger.warning.call_args.kwargs
        assert mock_logger.warning.call_args.args[0] == "output_guardrail_violation"
        assert "CALCULATION_WITHOUT_WIZARD" in log_kwargs["warning_flags"]
        assert log_kwargs["has_calculation_violation"] is True

        added_items = [call.args[0] for call in mock_db.add.call_args_list]
        msg = next(item for item in added_items if isinstance(item, ChatMessage))
        assert msg.sources is not None
        assert "CALCULATION_WITHOUT_WIZARD" in msg.sources[0].get("audit_flags", [])

    @pytest.mark.asyncio
    async def test_full_chat_api_dispatches_output_guardrails_in_background(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_db: AsyncMock,
        mock_retrieved_chunk: RetrievedChunk,
    ) -> None:
        """Endpoint /api/v1/chat deve responder imediatamente ao cliente e executar guardrails em background."""
        session_id = uuid4()
        now = datetime.now(UTC)
        active_session = ChatSession(id=session_id, created_at=now, updated_at=now)

        def _mock_execute(stmt: Any, *args: Any, **kwargs: Any) -> MagicMock:
            stmt_str = str(stmt).lower()
            if "chat_messages" in stmt_str or "chatmessage" in stmt_str:
                res = MagicMock()
                res.scalars.return_value.all.return_value = []
                return res
            res = MagicMock()
            res.scalar_one_or_none.return_value = active_session
            return res

        mock_db.execute.side_effect = _mock_execute

        mock_rag_result = RetrievalResult(
            query="qual a demanda?",
            chunks=[mock_retrieved_chunk],
            is_contingency=False,
        )

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="A demanda é de exatos 142,5 kVA [Fonte: DIS-NOR-030, Item 99.4]."
            )
        )

        mock_orchestrator = AsyncMock(spec=RagContextOrchestrator)
        mock_orchestrator.get_context.return_value = mock_rag_result

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_db
        mock_cm.__aexit__.return_value = None

        with (
            patch("lumi.services.chat_service.get_llm", return_value=mock_llm),
            patch(
                "lumi.services.chat_service.create_rag_orchestrator",
                return_value=mock_orchestrator,
            ),
            patch("lumi.services.analytics_service.get_db_session", return_value=mock_cm),
            patch("lumi.services.analytics_service.logger") as mock_analytics_logger,
        ):
            payload = {
                "session_id": str(session_id),
                "message": "Qual é a demanda do prédio?",
                "stream": False,
            }

            # A resposta HTTP deve ser 200 imediata sem bloqueio
            response = await async_client.post("/api/v1/chat", json=payload, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "142,5 kVA" in data["response"]

            # Aguarda a tarefa assíncrona BackgroundTasks completar no loop
            await asyncio.sleep(0.05)

            # O worker de background deve ter emitido o alerta com ambas as violações
            violation_calls = [
                c for c in mock_analytics_logger.warning.call_args_list
                if c.args and c.args[0] == "output_guardrail_violation"
            ]
            assert len(violation_calls) == 1
            call_kwargs = violation_calls[0].kwargs
            assert "HALLUCINATED_CITATION" in call_kwargs["warning_flags"]
            assert "CALCULATION_WITHOUT_WIZARD" in call_kwargs["warning_flags"]
