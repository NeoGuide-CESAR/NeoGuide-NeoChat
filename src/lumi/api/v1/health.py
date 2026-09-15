"""Endpoint de health check avançado e diagnóstico do sistema (v1)."""

import time
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from lumi import __version__
from lumi.api.deps import api_key_and_rate_limit
from lumi.core.config import get_settings
from lumi.db.session import get_async_session, sanitize_db_error
from lumi.schemas.health import DatabaseHealthInfo, HealthCheckResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": HealthCheckResponse,
            "description": "Sistema saudável ou degradado",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": HealthCheckResponse,
            "description": "Sistema com falha crítica no banco de dados",
        },
    },
    summary="Diagnóstico avançado de conectividade e extensões",
    description=(
        "Executa teste ativo de conectividade com o PostgreSQL (SELECT 1), "
        "mensura a latência em milissegundos e valida a instalação da extensão pgvector. "
        "Requer autenticação via X-API-Key."
    ),
)
async def get_health_check(
    response: Response,
    _auth: Annotated[str, Depends(api_key_and_rate_limit)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> HealthCheckResponse:
    """Realiza verificação profunda de integridade do sistema e banco de dados."""
    settings = get_settings()
    now_utc = datetime.now(UTC)

    try:
        # 1. Medição de latência com consulta leve
        start_time = time.perf_counter()
        await session.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # 2. Verificação da extensão vetorial pgvector
        pgvector_query = text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ext_result = await session.execute(pgvector_query)
        ext_version_val = ext_result.scalar()

        pgvector_installed = ext_version_val is not None
        pgvector_version = str(ext_version_val) if ext_version_val is not None else None

        overall_status = "healthy" if pgvector_installed else "degraded"

        return HealthCheckResponse(
            status=overall_status,
            version=__version__,
            environment=settings.environment,
            timestamp=now_utc,
            database=DatabaseHealthInfo(
                status="connected",
                latency_ms=latency_ms,
                pgvector_installed=pgvector_installed,
                pgvector_version=pgvector_version,
                error=None,
            ),
        )

    except Exception as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        sanitized_msg = sanitize_db_error(exc)

        return HealthCheckResponse(
            status="unhealthy",
            version=__version__,
            environment=settings.environment,
            timestamp=now_utc,
            database=DatabaseHealthInfo(
                status="error",
                latency_ms=None,
                pgvector_installed=False,
                pgvector_version=None,
                error=sanitized_msg,
            ),
        )
