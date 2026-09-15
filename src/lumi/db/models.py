"""Modelos declarativos SQLAlchemy 2.0 e esquemas relacionais/vetoriais."""

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR, JSON, TypeDecorator

# Fallback/variante transparente de JSONB para compatibilidade com SQLite em testes
JSON_FIELD_TYPE = JSONB().with_variant(JSON(), "sqlite")


# Compilador customizado para pgvector no SQLite (útil em testes unitários in-memory)
@compiles(Vector, "sqlite")
def _compile_vector_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    return "BLOB"


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(value))
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value


class Base(DeclarativeBase):
    """Classe base declarativa central para todos os modelos da aplicação."""

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()
        for key, value in kwargs.items():
            setattr(self, key, value)


class NormativeDocument(Base):
    """Documento técnico normativo (ex.: DIS-NOR-030, DIS-NOR-053)."""

    __tablename__ = "normative_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    revision: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relacionamento 1:N com NormativeChunk com cascade delete
    chunks: Mapped[list["NormativeChunk"]] = relationship(
        "NormativeChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class NormativeChunk(Base):
    """Trecho/bloco de conteúdo textual vetorizado de um documento normativo."""

    __tablename__ = "normative_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("normative_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    embedding = mapped_column(
        Vector(768),
        nullable=True,
    )
    section_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    section_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # Atributo nomeado como metadata_ para não conflitar com Base.metadata
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_FIELD_TYPE,
        nullable=False,
        default=dict,
    )

    # Relacionamento N:1 com NormativeDocument
    document: Mapped["NormativeDocument"] = relationship(
        "NormativeDocument",
        back_populates="chunks",
    )

    __table_args__ = (
        Index(
            "ix_normative_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class ChatSession(Base):
    """Sessão de conversação e interação do usuário com o assistente normativo."""

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relacionamento 1:N com ChatMessage ordenado temporalmente
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
        passive_deletes=True,
    )


class ChatMessage(Base):
    """Mensagem individual enviada pelo usuário ou gerada pelo assistente técnico."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON_FIELD_TYPE,
        nullable=True,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relacionamento N:1 com ChatSession
    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="messages",
    )

    __table_args__ = (
        Index(
            "ix_chat_messages_session_created",
            "session_id",
            "created_at",
        ),
    )


class NormativeQueryAnalytics(Base):
    """Métricas analíticas de telemetria e recuperação de consultas normativas."""

    __tablename__ = "normative_query_analytics"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    query_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    top_document_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    top_similarity_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
