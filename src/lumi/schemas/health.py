"""Schemas de diagnóstico e health check da API Lumi NeoGuide."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class DatabaseHealthInfo(BaseModel):
    """Informações detalhadas sobre o estado de saúde e conectividade do banco de dados."""

    status: Literal["connected", "disconnected", "error"] = Field(
        description="Estado da conexão com o banco de dados"
    )
    latency_ms: float | None = Field(
        default=None,
        description="Latência em milissegundos para consulta de verificação (SELECT 1)",
    )
    pgvector_installed: bool = Field(
        default=False,
        description="Indica se a extensão pgvector está instalada no PostgreSQL",
    )
    pgvector_version: str | None = Field(
        default=None,
        description="Versão identificada da extensão pgvector",
    )
    error: str | None = Field(
        default=None,
        description="Mensagem descritiva e sanitizada em caso de erro de conexão",
    )


class HealthCheckResponse(BaseModel):
    """Contrato de resposta estruturada para o diagnóstico e integridade do sistema."""

    status: Literal["healthy", "unhealthy", "degraded"] = Field(
        description="Status operacional consolidado do serviço"
    )
    version: str = Field(description="Versão da aplicação Lumi NeoGuide")
    environment: str = Field(description="Ambiente de execução (development, staging, production)")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC da realização do diagnóstico",
    )
    database: DatabaseHealthInfo = Field(
        description="Diagnóstico específico do banco de dados PostgreSQL"
    )
