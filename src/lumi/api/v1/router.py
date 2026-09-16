"""Roteador principal da versão 1 (v1) da API Lumi NeoGuide."""

from fastapi import APIRouter

from lumi.api.v1.chat import router as chat_router
from lumi.api.v1.health import router as health_router
from lumi.api.v1.sessions import router as sessions_router

api_v1_router = APIRouter()

# Inclusão dos sub-roteadores da API v1
api_v1_router.include_router(health_router, prefix="", tags=["Diagnóstico v1"])
api_v1_router.include_router(sessions_router, prefix="/sessions", tags=["Sessões v1"])
api_v1_router.include_router(chat_router, prefix="/chat", tags=["Chat v1"])
