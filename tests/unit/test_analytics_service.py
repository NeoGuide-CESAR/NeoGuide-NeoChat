"""Testes unitários para o AnalyticsService e rotina assíncrona persist_interaction_background."""

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lumi.db.models import ChatMessage, ChatSession, NormativeQueryAnalytics
from lumi.services.analytics_service import AnalyticsService, persist_interaction_background


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock de sessão assíncrona do SQLAlchemy."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


class TestAnalyticsService:
    """Testes unitários para a classe AnalyticsService."""

    @pytest.mark.asyncio
    async def test_record_query_analytics_success(self, mock_db_session: AsyncMock) -> None:
        """Deve registrar métrica analítica corretamente com flush no banco."""
        service = AnalyticsService(session=mock_db_session)
        session_id = uuid.uuid4()

        record = await service.record_query_analytics(
            session_id=session_id,
            query_text="Qual a distância mínima de segurança para rede aérea?",
            latency_ms=350,
            top_document_code="DIS-NOR-030",
            top_similarity_score=0.91,
        )

        assert record.session_id == session_id
        assert record.query_text == "Qual a distância mínima de segurança para rede aérea?"
        assert record.latency_ms == 350
        assert record.top_document_code == "DIS-NOR-030"
        assert record.top_similarity_score == 0.91
        assert isinstance(record.created_at, datetime)

        mock_db_session.add.assert_called_once_with(record)
        mock_db_session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_query_analytics_with_defaults(self, mock_db_session: AsyncMock) -> None:
        """Deve registrar métrica analítica com valores opcionais nulos (ex.: recusa/contingência)."""
        service = AnalyticsService(session=mock_db_session)

        record = await service.record_query_analytics(
            query_text="Pergunta sem correspondência normativa",
            latency_ms=45,
            session_id=None,
            top_document_code=None,
            top_similarity_score=None,
        )

        assert record.session_id is None
        assert record.top_document_code is None
        assert record.top_similarity_score is None
        assert record.latency_ms == 45
        mock_db_session.add.assert_called_once_with(record)


class TestPersistInteractionBackground:
    """Testes unitários para a rotina desacoplada persist_interaction_background."""

    @pytest.mark.asyncio
    async def test_persist_interaction_success(self) -> None:
        """Persistência em background bem-sucedida deve gravar mensagem e analytics."""
        session_id = uuid.uuid4()
        now = datetime.now(UTC)
        mock_session_obj = ChatSession(id=session_id, created_at=now, updated_at=now)

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session_obj
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        mock_factory = MagicMock(spec=async_sessionmaker)
        mock_factory.return_value = mock_db

        sources = [
            {
                "document_code": "DIS-NOR-030",
                "page": 12,
                "section": "Item 4",
                "relevance_score": 0.88,
            }
        ]

        # Patch get_db_session para injetar mock_db
        with patch("lumi.services.analytics_service.get_db_session") as mock_get_db:
            # Context manager assíncrono mock
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_db
            mock_cm.__aexit__.return_value = None
            mock_get_db.return_value = mock_cm

            success = await persist_interaction_background(
                session_id=session_id,
                query_text="Como calcular o ramal de entrada?",
                assistant_message="Conforme a norma DIS-NOR-030...",
                sources=sources,
                top_document_code="DIS-NOR-030",
                top_similarity_score=0.88,
                latency_ms=420,
                retry_backoff_seconds=0.001,
            )

        assert success is True
        # Mensagem do assistente e registro de analytics adicionados
        assert mock_db.add.call_count == 2

        added_items = [call.args[0] for call in mock_db.add.call_args_list]
        msg = next(item for item in added_items if isinstance(item, ChatMessage))
        analytics = next(item for item in added_items if isinstance(item, NormativeQueryAnalytics))

        assert msg.session_id == session_id
        assert msg.role == "assistant"
        assert msg.content == "Conforme a norma DIS-NOR-030..."
        assert msg.sources == sources

        assert analytics.session_id == session_id
        assert analytics.query_text == "Como calcular o ramal de entrada?"
        assert analytics.top_document_code == "DIS-NOR-030"
        assert analytics.top_similarity_score == 0.88
        assert analytics.latency_ms == 420

    @pytest.mark.asyncio
    async def test_persist_interaction_retry_on_transient_failure(self) -> None:
        """Deve retentar após erro na 1ª tentativa e concluir com sucesso na 2ª tentativa."""
        session_id = uuid.uuid4()
        now = datetime.now(UTC)
        mock_session_obj = ChatSession(id=session_id, created_at=now, updated_at=now)

        mock_db_success = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session_obj
        mock_db_success.execute.return_value = mock_result
        mock_db_success.add = MagicMock()
        mock_db_success.flush = AsyncMock()

        attempt_count = 0

        class MockDbSessionContext:
            async def __aenter__(self) -> AsyncSession:
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count == 1:
                    raise ConnectionResetError("Conexão com banco interrompida temporariamente")
                return mock_db_success

            async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        with patch(
            "lumi.services.analytics_service.get_db_session",
            return_value=MockDbSessionContext(),
        ):
            success = await persist_interaction_background(
                session_id=session_id,
                query_text="Pergunta teste",
                assistant_message="Resposta teste",
                sources=[],
                latency_ms=100,
                max_retries=1,
                retry_backoff_seconds=0.001,
            )

        assert success is True
        assert attempt_count == 2
        assert mock_db_success.add.call_count == 2

    @pytest.mark.asyncio
    async def test_persist_interaction_failure_after_max_retries_silenced(self) -> None:
        """Falha após esgotar retentativas deve logar erro e retornar False sem levantar exceção."""
        session_id = uuid.uuid4()

        class MockFailingContext:
            async def __aenter__(self) -> AsyncSession:
                raise RuntimeError("Falha irreversível no banco de dados")

            async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                pass

        with patch(
            "lumi.services.analytics_service.get_db_session",
            return_value=MockFailingContext(),
        ):
            success = await persist_interaction_background(
                session_id=session_id,
                query_text="Pergunta com erro",
                assistant_message="Resposta",
                sources=[],
                latency_ms=50,
                max_retries=1,
                retry_backoff_seconds=0.001,
            )

        assert success is False
