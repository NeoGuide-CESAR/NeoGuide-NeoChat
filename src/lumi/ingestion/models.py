"""Data models for document ingestion and parsing."""

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DocumentPage(BaseModel):
    """Represents a single parsed page from a technical normative document."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1, description="Número da página (iniciando em 1)")
    raw_text: str = Field(description="Texto bruto extraído da página")
    clean_text: str = Field(description="Texto higienizado após sanitização")
    tables: list[str] = Field(
        default_factory=list,
        description="Lista de tabelas extraídas da página em formato Markdown",
    )


class ParsedDocument(BaseModel):
    """Represents a fully ingested and parsed normative document."""

    model_config = ConfigDict(frozen=True)

    document_code: str = Field(
        description="Código identificador da norma (ex.: 'DIS-NOR-030', 'DIS-NOR-053')"
    )
    title: str = Field(description="Título da norma técnica")
    revision: str = Field(description="Versão ou revisão da norma (ex.: '07' ou 'REV07')")
    company: str = Field(
        description="Distribuidora ou concessionária (ex.: 'Neoenergia Pernambuco')"
    )
    pages: list[DocumentPage] = Field(
        default_factory=list,
        description="Coleção de páginas estruturadas do documento",
    )
    full_clean_text: str = Field(
        description="Texto integral higienizado com marcadores de página inseridos"
    )
    source_file: str = Field(description="Caminho do arquivo de origem")


class NormativeChunkData(BaseModel):
    """Representa um fragmento (chunk) semântico estruturado de documento normativo."""

    model_config = ConfigDict(frozen=True)

    document_code: str = Field(
        description="Código identificador da norma (ex.: 'DIS-NOR-030', 'DIS-NOR-053')"
    )
    revision: str = Field(description="Versão ou revisão da norma (ex.: '07' ou 'REV07')")
    content: str = Field(description="Texto integral do chunk com cabeçalho contextual/breadcrumb")
    section_code: str | None = Field(
        default=None,
        description="Código da seção normativa ativa (ex.: '5.2', '6.7.16', 'Capítulo X')",
    )
    section_title: str | None = Field(
        default=None,
        description="Título da seção normativa ativa",
    )
    page_number: int | None = Field(
        default=None,
        ge=1,
        description="Número da página principal (iniciando em 1)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados adicionais (is_table, table_id, page_range, etc.)",
    )
    chunk_hash: str = Field(
        default="",
        description="Hash SHA-256 do conteúdo gerado para garantia de idempotência",
    )

    @model_validator(mode="before")
    @classmethod
    def _compute_chunk_hash(cls, values: Any) -> Any:
        if isinstance(values, dict):
            content = values.get("content")
            chunk_hash = values.get("chunk_hash")
            if not chunk_hash and content is not None:
                values["chunk_hash"] = hashlib.sha256(str(content).encode("utf-8")).hexdigest()
        return values
