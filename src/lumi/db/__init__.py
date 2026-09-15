"""Módulo de persistência, modelos relacionais/vetoriais e sessões do Lumi NeoGuide."""

from lumi.db.models import (
    Base,
    ChatMessage,
    ChatSession,
    NormativeChunk,
    NormativeDocument,
    NormativeQueryAnalytics,
)
from lumi.db.session import (
    async_session_factory,
    create_app_engine,
    engine,
    get_db,
    get_db_session,
)

__all__ = [
    "Base",
    "NormativeDocument",
    "NormativeChunk",
    "ChatSession",
    "ChatMessage",
    "NormativeQueryAnalytics",
    "engine",
    "create_app_engine",
    "async_session_factory",
    "get_db_session",
    "get_db",
]
