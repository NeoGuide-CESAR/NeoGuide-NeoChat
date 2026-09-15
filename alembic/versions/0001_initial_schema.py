"""Esquema inicial com suporte a pgvector, documentos, chunks, chat e analíticos.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-14 23:55:00.000000

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Identificadores de revisão do Alembic
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Habilita a extensão pgvector para armazenamento e busca de embeddings
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Tabela de Documentos Normativos Técnicos
    op.create_table(
        "normative_documents",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("revision", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_normative_documents_code",
        "normative_documents",
        ["code"],
        unique=True,
    )

    # 3. Tabela de Chunks Normativos com Vetores de 768 Dimensões
    op.create_table(
        "normative_chunks",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "document_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("normative_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(768), nullable=True),
        sa.Column("section_code", sa.String(50), nullable=True),
        sa.Column("section_title", sa.String(255), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "ix_normative_chunks_document_id",
        "normative_chunks",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_normative_chunks_embedding_hnsw",
        "normative_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # 4. Tabela de Sessões Conversacionais
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 5. Tabela de Mensagens do Chat com Histórico Temporal
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "session_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_messages_session_id",
        "chat_messages",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_session_created",
        "chat_messages",
        ["session_id", "created_at"],
        unique=False,
    )

    # 6. Tabela de Métricas e Observabilidade de Consultas Normativas
    op.create_table(
        "normative_query_analytics",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "session_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("top_document_code", sa.String(50), nullable=True),
        sa.Column("top_similarity_score", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_normative_query_analytics_session_id",
        "normative_query_analytics",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    # Remove as tabelas em ordem reversa para respeitar as foreign keys
    op.drop_table("normative_query_analytics")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("normative_chunks")
    op.drop_table("normative_documents")

    # Remove a extensão pgvector caso desejado
    op.execute("DROP EXTENSION IF EXISTS vector")
