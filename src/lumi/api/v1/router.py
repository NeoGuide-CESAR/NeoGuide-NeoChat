"""Roteador principal da versão 1 (v1) da API Lumi NeoGuide."""

from fastapi import APIRouter

from lumi.api.v1.health import router as health_router

api_v1_router = APIRouter()

# Inclusão dos sub-roteadores da API v1
api_v1_router.include_router(health_router, prefix="", tags=["Diagnóstico v1"])
