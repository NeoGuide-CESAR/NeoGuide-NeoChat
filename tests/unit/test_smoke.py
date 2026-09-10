"""Smoke tests para validar inicialização e respostas básicas da API Lumi."""

import pytest
from httpx import AsyncClient

from lumi import __version__
from lumi.core.config import get_settings


def test_package_version() -> None:
    """Valida se a versão do pacote está definida corretamente."""
    assert __version__ == "0.1.0"


def test_settings_defaults() -> None:
    """Valida se as configurações padrões do Settings estão corretas."""
    settings = get_settings()
    assert settings.environment == "development"
    assert settings.api_port == 8000
    assert "postgresql+asyncpg" in settings.database_url
    assert settings.similarity_threshold == 0.70


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient) -> None:
    """Valida endpoint raiz GET /."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Lumi API"
    assert data["status"] == "online"
    assert data["version"] == __version__


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    """Valida endpoint GET /health."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == __version__
