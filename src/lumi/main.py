"""Ponto de entrada da aplicação FastAPI do Lumi NeoGuide."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lumi import __version__
from lumi.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Lumi (NeoGuide) API",
    description="Assistente Normativo Inteligente para Infraestrutura de Telecomunicações",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Diagnóstico"])
async def root() -> dict[str, str]:
    """Endpoint raiz com informações de integridade básica do serviço."""
    return {
        "service": "Lumi API",
        "version": __version__,
        "status": "online",
        "environment": settings.environment,
    }


@app.get("/health", tags=["Diagnóstico"])
async def health() -> dict[str, str]:
    """Endpoint de health check do serviço."""
    return {
        "status": "healthy",
        "version": __version__,
    }
