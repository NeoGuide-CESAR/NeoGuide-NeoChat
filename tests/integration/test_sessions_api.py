"""Testes de integração para os endpoints REST de sessões (/api/v1/sessions)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.api.deps import get_db, get_db_session
from lumi.core.config import get_settings
from lumi.db.models import ChatMessage, ChatSession
from lumi.main import app


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


class TestSessionsApiAuthentication:
    """Valida a proteção dos endpoints de sessão por chave de API (X-API-Key)."""

    @pytest.mark.asyncio
    async def test_post_session_missing_api_key(self, async_client: AsyncClient) -> None:
        """Requisição POST /api/v1/sessions sem header deve falhar com HTTP 401."""
        response = await async_client.post("/api/v1/sessions")
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API Key"

    @pytest.mark.asyncio
    async def test_post_session_invalid_api_key(self, async_client: AsyncClient) -> None:
        """Requisição POST /api/v1/sessions com chave errada deve falhar com HTTP 401."""
        headers = {"X-API-Key": "invalid-api-key-test"}
        response = await async_client.post("/api/v1/sessions", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API Key"

    @pytest.mark.asyncio
    async def test_get_session_missing_api_key(self, async_client: AsyncClient) -> None:
        """Requisição GET /api/v1/sessions/{id} sem header deve falhar com HTTP 401."""
        session_id = uuid4()
        response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or missing API Key"


class TestSessionsApiEndpoints:
    """Valida o funcionamento dos métodos POST e GET de sessões."""

    @pytest.mark.asyncio
    async def test_create_session_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], mock_db: AsyncMock
    ) -> None:
        """POST /api/v1/sessions deve retornar 201 Created com SessionCreateResponse."""
        response = await async_client.post("/api/v1/sessions", headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "created_at" in data
        assert mock_db.add.called
        assert mock_db.flush.called

    @pytest.mark.asyncio
    async def test_get_session_detail_success(
        self, async_client: AsyncClient, auth_headers: dict[str, str], mock_db: AsyncMock
    ) -> None:
        """GET /api/v1/sessions/{id} deve retornar 200 OK com SessionDetailResponse e histórico."""
        session_id = uuid4()
        now = datetime.now(UTC)
        session = ChatSession(id=session_id, created_at=now, updated_at=now)

        msg1 = ChatMessage(
            session_id=session_id,
            role="user",
            content="Como calcular queda de tensão?",
            sources=[],
            created_at=now - timedelta(minutes=2),
        )
        msg2 = ChatMessage(
            session_id=session_id,
            role="assistant",
            content="Conforme DIS-NOR-030...",
            sources=[{"code": "DIS-NOR-030", "title": "Redes", "score": 0.9}],
            created_at=now - timedelta(minutes=1),
        )

        mock_session_res = MagicMock()
        mock_session_res.scalar_one_or_none.return_value = session

        mock_msgs_res = MagicMock()
        mock_msgs_res.scalars.return_value.all.return_value = [msg1, msg2]

        mock_db.execute.side_effect = [mock_session_res, mock_msgs_res]

        response = await async_client.get(f"/api/v1/sessions/{session_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(session_id)
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Como calcular queda de tensão?"
        assert data["messages"][1]["role"] == "assistant"
        assert len(data["messages"][1]["sources"]) == 1
        assert data["messages"][1]["sources"][0]["document_code"] == "DIS-NOR-030"

    @pytest.mark.asyncio
    async def test_get_session_not_found(
        self, async_client: AsyncClient, auth_headers: dict[str, str], mock_db: AsyncMock
    ) -> None:
        """GET /api/v1/sessions/{id} com ID inexistente deve retornar HTTP 404 Not Found."""
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_res

        target_id = uuid4()
        response = await async_client.get(f"/api/v1/sessions/{target_id}", headers=auth_headers)

        assert response.status_code == 404
        assert "não encontrada" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_session_expired_returns_410_gone(
        self, async_client: AsyncClient, auth_headers: dict[str, str], mock_db: AsyncMock
    ) -> None:
        """GET /api/v1/sessions/{id} com sessão inativa há > 1h deve retornar HTTP 410 Gone."""
        session_id = uuid4()
        expired_time = datetime.now(UTC) - timedelta(hours=1, minutes=15)
        expired_session = ChatSession(
            id=session_id,
            created_at=expired_time - timedelta(hours=1),
            updated_at=expired_time,
        )

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = expired_session
        mock_db.execute.return_value = mock_res

        response = await async_client.get(f"/api/v1/sessions/{session_id}", headers=auth_headers)

        assert response.status_code == 410
        assert response.json()["detail"] == "Sessão expirada por inatividade."
