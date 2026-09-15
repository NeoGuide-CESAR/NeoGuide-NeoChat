"""Testes unitários para os endpoints de health check e diagnóstico do sistema."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError

from lumi import __version__
from lumi.core.config import get_settings
from lumi.db.session import get_async_session
from lumi.main import app
from lumi.schemas.health import DatabaseHealthInfo, HealthCheckResponse


@pytest.fixture
def valid_headers() -> dict[str, str]:
    """Retorna cabeçalhos com chave de API válida."""
    settings = get_settings()
    return {"X-API-Key": settings.api_key}


@pytest.fixture
def invalid_headers() -> dict[str, str]:
    """Retorna cabeçalhos com chave de API inválida."""
    return {"X-API-Key": "chave-totalmente-invalida"}


@pytest.mark.asyncio
async def test_root_health_endpoint_remains_unauthenticated(async_client: AsyncClient) -> None:
    """Garante que GET /health na raiz continue funcionando sem exigir autenticação."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == __version__


@pytest.mark.asyncio
async def test_api_v1_health_requires_authentication(async_client: AsyncClient) -> None:
    """Garante que GET /api/v1/health sem header X-API-Key retorne 401 Unauthorized."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid or missing API Key"


@pytest.mark.asyncio
async def test_api_v1_health_rejects_invalid_api_key(
    async_client: AsyncClient, invalid_headers: dict[str, str]
) -> None:
    """Garante que GET /api/v1/health com chave inválida retorne 401 Unauthorized."""
    response = await async_client.get("/api/v1/health", headers=invalid_headers)
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid or missing API Key"


@pytest.mark.asyncio
async def test_api_v1_health_healthy_with_pgvector(
    async_client: AsyncClient, valid_headers: dict[str, str]
) -> None:
    """Garante resposta 200 healthy quando banco e pgvector estão operacionais."""
    mock_session = AsyncMock()

    mock_result_select_1 = MagicMock()
    mock_result_select_1.scalar.return_value = 1

    mock_result_pgvector = MagicMock()
    mock_result_pgvector.scalar.return_value = "0.7.0"

    mock_session.execute.side_effect = [mock_result_select_1, mock_result_pgvector]

    async def override_get_session() -> AsyncGenerator[AsyncMock, None]:
        yield mock_session

    app.dependency_overrides[get_async_session] = override_get_session
    try:
        response = await async_client.get("/api/v1/health", headers=valid_headers)
        assert response.status_code == 200
        data = response.json()

        # Validação com modelo Pydantic
        health_resp = HealthCheckResponse.model_validate(data)
        assert isinstance(health_resp.database, DatabaseHealthInfo)
        assert health_resp.status == "healthy"
        assert health_resp.version == __version__
        assert health_resp.environment == get_settings().environment
        assert health_resp.database.status == "connected"
        assert health_resp.database.pgvector_installed is True
        assert health_resp.database.pgvector_version == "0.7.0"
        assert health_resp.database.latency_ms is not None
        assert health_resp.database.latency_ms >= 0.0
        assert health_resp.database.error is None
    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_api_v1_health_degraded_when_pgvector_missing(
    async_client: AsyncClient, valid_headers: dict[str, str]
) -> None:
    """Garante resposta 200 degraded com pgvector_installed=False quando a extensão não existe."""
    mock_session = AsyncMock()

    mock_result_select_1 = MagicMock()
    mock_result_select_1.scalar.return_value = 1

    mock_result_pgvector = MagicMock()
    mock_result_pgvector.scalar.return_value = None

    mock_session.execute.side_effect = [mock_result_select_1, mock_result_pgvector]

    async def override_get_session() -> AsyncGenerator[AsyncMock, None]:
        yield mock_session

    app.dependency_overrides[get_async_session] = override_get_session
    try:
        response = await async_client.get("/api/v1/health", headers=valid_headers)
        assert response.status_code == 200
        data = response.json()

        health_resp = HealthCheckResponse.model_validate(data)
        assert health_resp.status == "degraded"
        assert health_resp.database.status == "connected"
        assert health_resp.database.pgvector_installed is False
        assert health_resp.database.pgvector_version is None
        assert health_resp.database.latency_ms is not None
        assert health_resp.database.error is None
    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_api_v1_health_unhealthy_on_database_failure(
    async_client: AsyncClient, valid_headers: dict[str, str]
) -> None:
    """Garante resposta 503 unhealthy e mensagem sanitizada quando ocorre falha no banco."""
    mock_session = AsyncMock()
    sensitive_db_url = (
        "postgresql+asyncpg://postgres:super_secret_password@db.internal:5432/lumi_db"
    )
    mock_session.execute.side_effect = OperationalError(
        f"connection to server at '{sensitive_db_url}' failed: Connection refused",
        None,
        Exception("Connection refused"),
    )

    async def override_get_session() -> AsyncGenerator[AsyncMock, None]:
        yield mock_session

    app.dependency_overrides[get_async_session] = override_get_session
    try:
        response = await async_client.get("/api/v1/health", headers=valid_headers)
        assert response.status_code == 503
        data = response.json()

        health_resp = HealthCheckResponse.model_validate(data)
        assert health_resp.status == "unhealthy"
        assert health_resp.database.status in ("error", "disconnected")
        assert health_resp.database.pgvector_installed is False
        assert health_resp.database.latency_ms is None
        assert health_resp.database.error is not None
        # Confirma sanitização: não pode vazar a senha sensível
        assert "super_secret_password" not in health_resp.database.error
    finally:
        app.dependency_overrides.pop(get_async_session, None)
