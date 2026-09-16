"""Testes de integração para o endpoint de chat (/api/v1/chat)."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from langchain_core.messages import AIMessageChunk
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.api.deps import get_db, get_db_session
from lumi.core.config import get_settings
from lumi.db.models import ChatSession
from lumi.main import app
from lumi.rag.chains import RagContextOrchestrator
from lumi.rag.retriever import RetrievalResult, RetrievedChunk


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock da sessão do banco de dados para injeção de dependência."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    return db


@pytest.fixture(autouse=True)
def override_db_dependency(mock_db: AsyncMock):
    """Sobrescreve a dependência de banco de dados no FastAPI para todos os testes."""

    async def _override():
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
def mock_rag_result() -> RetrievalResult:
    """Fixture com resultado de recuperação RAG válido."""
    chunk = RetrievedChunk(
        chunk_id=uuid4(),
        document_code="DIS-NOR-030",
        document_title="Norma Técnica de Distribuição",
        revision="REV07",
        section_code="Item 4.1",
        section_title="Dimensionamento Geral",
        page_number=10,
        content="Critérios técnicos normativos da Neoenergia.",
        similarity_score=0.92,
        metadata={},
    )
    return RetrievalResult(
        query="teste",
        chunks=[chunk],
        is_contingency=False,
    )


class TestChatApiAuthentication:
    """Valida a proteção do endpoint POST /api/v1/chat por chave de API (X-API-Key)."""

    @pytest.mark.asyncio
    async def test_post_chat_missing_api_key(self, async_client: AsyncClient) -> None:
        """Requisição sem cabeçalho X-API-Key deve falhar com HTTP 401."""
        payload = {
            "session_id": str(uuid4()),
            "message": "Qual é o limite de queda de tensão?",
            "stream": True,
        }
        response = await async_client.post("/api/v1/chat", json=payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API Key"

    @pytest.mark.asyncio
    async def test_post_chat_invalid_api_key(self, async_client: AsyncClient) -> None:
        """Requisição com chave inválida deve falhar com HTTP 401."""
        payload = {
            "session_id": str(uuid4()),
            "message": "Qual é o limite de queda de tensão?",
            "stream": True,
        }
        headers = {"X-API-Key": "invalid-api-key"}
        response = await async_client.post("/api/v1/chat", json=payload, headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API Key"


class TestChatApiSessionValidation:
    """Valida as restrições de ciclo de vida da sessão (404 e 410)."""

    @pytest.mark.asyncio
    async def test_post_chat_session_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_db: AsyncMock,
    ) -> None:
        """Sessão inexistente deve retornar HTTP 404 Not Found."""
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        session_id = uuid4()
        payload = {
            "session_id": str(session_id),
            "message": "Qual é a norma aplicável?",
            "stream": True,
        }

        response = await async_client.post("/api/v1/chat", json=payload, headers=auth_headers)
        assert response.status_code == 404
        assert "não encontrada" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_post_chat_session_expired(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_db: AsyncMock,
    ) -> None:
        """Sessão com inatividade > 1h deve retornar HTTP 410 Gone."""
        session_id = uuid4()
        now = datetime.now(UTC)
        expired_time = now - timedelta(hours=1, minutes=10)
        expired_session = ChatSession(
            id=session_id,
            created_at=expired_time - timedelta(hours=1),
            updated_at=expired_time,
        )

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = expired_session
        mock_db.execute.return_value = mock_res

        payload = {
            "session_id": str(session_id),
            "message": "Pergunta em sessão expirada",
            "stream": True,
        }

        response = await async_client.post("/api/v1/chat", json=payload, headers=auth_headers)
        assert response.status_code == 410
        assert response.json()["detail"] == "Sessão expirada por inatividade."


class TestChatApiExecution:
    """Valida o processamento de requisições streaming SSE e síncronas."""

    @pytest.mark.asyncio
    async def test_post_chat_streaming_sse_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_db: AsyncMock,
        mock_rag_result: RetrievalResult,
    ) -> None:
        """POST /api/v1/chat com stream=true deve retornar 200 text/event-stream e eventos SSE válidos."""
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

        # Mock do RAG e da LLM
        mock_llm = MagicMock()

        async def _mock_astream(*args: Any, **kwargs: Any) -> AsyncGenerator[AIMessageChunk, None]:
            yield AIMessageChunk(content="De acordo ")
            yield AIMessageChunk(content="com a DIS-NOR-030.")

        mock_llm.astream = _mock_astream

        mock_orchestrator = AsyncMock(spec=RagContextOrchestrator)
        mock_orchestrator.get_context.return_value = mock_rag_result

        with (
            patch("lumi.services.chat_service.get_llm", return_value=mock_llm),
            patch(
                "lumi.services.chat_service.create_rag_orchestrator", return_value=mock_orchestrator
            ),
        ):
            payload = {
                "session_id": str(session_id),
                "message": "Qual é a norma de ligação predial?",
                "stream": True,
            }

            response = await async_client.post("/api/v1/chat", json=payload, headers=auth_headers)

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            assert "no-cache" in response.headers.get("cache-control", "")
            assert "keep-alive" in response.headers.get("connection", "").lower()

            body_text = response.text
            assert "event: token" in body_text
            assert "event: sources" in body_text
            assert "event: done" in body_text
            assert "DIS-NOR-030" in body_text

    @pytest.mark.asyncio
    async def test_post_chat_synchronous_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_db: AsyncMock,
        mock_rag_result: RetrievalResult,
    ) -> None:
        """POST /api/v1/chat com stream=false deve retornar HTTP 200 e payload JSON ChatResponse."""
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

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Resposta técnica síncrona."))

        mock_orchestrator = AsyncMock(spec=RagContextOrchestrator)
        mock_orchestrator.get_context.return_value = mock_rag_result

        with (
            patch("lumi.services.chat_service.get_llm", return_value=mock_llm),
            patch(
                "lumi.services.chat_service.create_rag_orchestrator", return_value=mock_orchestrator
            ),
        ):
            payload = {
                "session_id": str(session_id),
                "message": "Como dimensionar ramal elétrico?",
                "stream": False,
            }

            response = await async_client.post("/api/v1/chat", json=payload, headers=auth_headers)

            assert response.status_code == 200
            assert "application/json" in response.headers.get("content-type", "")
            data = response.json()
            assert data["session_id"] == str(session_id)
            assert data["response"] == "Resposta técnica síncrona."
            assert len(data["sources"]) == 1
            assert data["sources"][0]["document_code"] == "DIS-NOR-030"
            assert "created_at" in data
