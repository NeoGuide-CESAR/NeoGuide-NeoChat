"""Ponto de entrada da aplicação FastAPI do Lumi NeoGuide."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lumi import __version__
from lumi.api.deps import api_key_and_rate_limit
from lumi.api.v1.router import api_v1_router
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

# Registro de Roteadores da API
app.include_router(api_v1_router, prefix="/api/v1")


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


@app.get("/api/v1/auth/check", tags=["Autenticação"])
async def auth_check(
    _api_key: str = Depends(api_key_and_rate_limit),
) -> dict[str, str]:
    """Endpoint de verificação de integridade da autenticação e limites de requisição."""
    return {
        "status": "authenticated",
        "message": "API Key is valid",
    }
