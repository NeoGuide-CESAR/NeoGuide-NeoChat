"""Dependências de segurança e controle de taxa para a API FastAPI."""

import asyncio
import math
import secrets
import time
from collections import defaultdict

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from lumi.core.config import get_settings

# Header de autenticação padrão da API Lumi
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """Valida a chave de API fornecida no header X-API-Key contra a configuração.

    Raises:
        HTTPException: 401 Unauthorized se a chave estiver ausente ou incorreta.

    Returns:
        str: A chave de API validada.
    """
    settings = get_settings()
    if not api_key or not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key


class RateLimiter:
    """Controlador de taxa de requisições por janela deslizante (sliding window) em memória."""

    def __init__(
        self,
        requests_per_minute: int | None = None,
        window_seconds: float = 60.0,
    ) -> None:
        self._requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._history: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    @property
    def requests_per_minute(self) -> int:
        """Retorna o limite configurado ou o padrão de Settings."""
        if self._requests_per_minute is not None:
            return self._requests_per_minute
        return get_settings().rate_limit_requests_per_minute

    def reset(self) -> None:
        """Limpa o histórico de requisições mantido em memória."""
        self._history.clear()

    async def check_rate_limit(self, identifier: str) -> None:
        """Verifica se o identificador excedeu o limite na janela deslizante.

        Raises:
            HTTPException: 429 Too Many Requests se o limite for atingido.
        """
        now = time.time()
        limit = self.requests_per_minute
        threshold = now - self.window_seconds

        async with self._lock:
            # Filtra registros fora da janela deslizante atual
            timestamps = [ts for ts in self._history[identifier] if ts > threshold]
            self._history[identifier] = timestamps

            if len(timestamps) >= limit:
                oldest_ts = timestamps[0]
                retry_after = max(1, math.ceil(oldest_ts + self.window_seconds - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)

    async def __call__(
        self,
        request: Request,
        api_key: str = Security(verify_api_key),
    ) -> str:
        """Ponto de entrada para uso como dependência direta do FastAPI."""
        identifier = api_key or (request.client.host if request.client else "anonymous")
        await self.check_rate_limit(identifier)
        return identifier


# Instância padrão de limitador de requisições da aplicação
default_rate_limiter = RateLimiter()


async def api_key_and_rate_limit(
    request: Request,
    api_key: str = Security(verify_api_key),
) -> str:
    """Dependência combinada que valida a API Key e aplica o rate-limiting."""
    identifier = api_key or (request.client.host if request.client else "anonymous")
    await default_rate_limiter.check_rate_limit(identifier)
    return api_key
