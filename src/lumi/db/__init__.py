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
    get_async_session,
    get_db,
    get_db_session,
    get_engine,
    get_session_factory,
    sanitize_db_error,
)
from lumi.db.vector_store import NormativeVectorStore

__all__ = [
    "Base",
    "NormativeDocument",
    "NormativeChunk",
    "NormativeVectorStore",
    "ChatSession",
    "ChatMessage",
    "NormativeQueryAnalytics",
    "engine",
    "create_app_engine",
    "async_session_factory",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "get_db",
    "get_async_session",
    "sanitize_db_error",
]
