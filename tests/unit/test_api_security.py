"""Testes unitários e de integração para segurança, autenticação por API Key, rate-limiting e CORS."""

import asyncio
import time
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from lumi.api.deps import RateLimiter, verify_api_key
from lumi.core.config import get_settings


@pytest.mark.asyncio
async def test_auth_check_missing_api_key(async_client: AsyncClient) -> None:
    """Valida que requisições sem o header X-API-Key retornam HTTP 401 Unauthorized."""
    response = await async_client.get("/api/v1/auth/check")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API Key"}


@pytest.mark.asyncio
async def test_auth_check_invalid_api_key(async_client: AsyncClient) -> None:
    """Valida que requisições com chave de API incorreta retornam HTTP 401 Unauthorized."""
    headers = {"X-API-Key": "chave-invalida-12345"}
    response = await async_client.get("/api/v1/auth/check", headers=headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API Key"}


@pytest.mark.asyncio
async def test_auth_check_valid_api_key(async_client: AsyncClient) -> None:
    """Valida que requisições com chave de API válida retornam HTTP 200 OK."""
    settings = get_settings()
    headers = {"X-API-Key": settings.api_key}
    response = await async_client.get("/api/v1/auth/check", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "authenticated"
    assert "valid" in data["message"].lower()


@pytest.mark.asyncio
async def test_verify_api_key_dependency_direct() -> None:
    """Valida a função verify_api_key diretamente."""
    settings = get_settings()

    # Chave válida
    result = await verify_api_key(api_key=settings.api_key)
    assert result == settings.api_key

    # Chave ausente
    with pytest.raises(HTTPException) as exc_missing:
        await verify_api_key(api_key=None)
    assert exc_missing.value.status_code == 401
    assert exc_missing.value.detail == "Invalid or missing API Key"

    # Chave errada
    with pytest.raises(HTTPException) as exc_wrong:
        await verify_api_key(api_key="chave-incorreta")
    assert exc_wrong.value.status_code == 401
    assert exc_wrong.value.detail == "Invalid or missing API Key"


@pytest.mark.asyncio
async def test_rate_limiter_burst_exceeded() -> None:
    """Valida que exceder o limite de requisições por minuto levanta HTTP 429 Too Many Requests."""
    limiter = RateLimiter(requests_per_minute=3, window_seconds=60.0)
    key = "test-client-key"

    # 3 requisições devem passar normalmente
    await limiter.check_rate_limit(key)
    await limiter.check_rate_limit(key)
    await limiter.check_rate_limit(key)

    # 4ª requisição na mesma janela deve falhar com 429
    with pytest.raises(HTTPException) as exc_info:
        await limiter.check_rate_limit(key)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "Rate limit exceeded. Try again later."
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_rate_limiter_reset_and_window_expiry() -> None:
    """Valida reset manual e passagem de tempo da janela deslizante do RateLimiter."""
    limiter = RateLimiter(requests_per_minute=2, window_seconds=60.0)
    key = "test-client-key"

    # Consome o limite
    await limiter.check_rate_limit(key)
    await limiter.check_rate_limit(key)

    with pytest.raises(HTTPException) as exc_info:
        await limiter.check_rate_limit(key)
    assert exc_info.value.status_code == 429

    # Reset manual
    limiter.reset()

    # Deve voltar a permitir requisições
    await limiter.check_rate_limit(key)

    # Simulação de avanço no tempo (passagem de janela deslizante)
    base_time = time.time()
    with patch("time.time", return_value=base_time):
        await limiter.check_rate_limit(key)
        with pytest.raises(HTTPException):
            await limiter.check_rate_limit(key)

    # 61 segundos depois (janela expirada)
    with patch("time.time", return_value=base_time + 61.0):
        # Deve permitir novamente sem erro
        await limiter.check_rate_limit(key)


@pytest.mark.asyncio
async def test_rate_limiter_concurrency() -> None:
    """Valida segurança em chamadas concorrentes assíncronas."""
    limiter = RateLimiter(requests_per_minute=10, window_seconds=60.0)
    key = "concurrent-client"

    # 10 tarefas paralelas devem ter sucesso
    results = await asyncio.gather(
        *(limiter.check_rate_limit(key) for _ in range(10)),
        return_exceptions=True,
    )
    assert all(r is None for r in results)

    # A 11ª chamada concorrente deve estourar o limite
    with pytest.raises(HTTPException) as exc_info:
        await limiter.check_rate_limit(key)
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_cors_preflight_allowed_origin(async_client: AsyncClient) -> None:
    """Valida preflight OPTIONS com origem configurada no settings.cors_origins."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-API-Key",
    }
    response = await async_client.options("/api/v1/auth/check", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "GET" in response.headers.get("access-control-allow-methods", "")
    assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_disallowed_origin(async_client: AsyncClient) -> None:
    """Valida preflight OPTIONS com origem não permitida."""
    headers = {
        "Origin": "http://unauthorized-attacker.com",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-API-Key",
    }
    response = await async_client.options("/api/v1/auth/check", headers=headers)
    # Origem não permitida não deve conter Access-Control-Allow-Origin
    assert response.headers.get("access-control-allow-origin") is None
