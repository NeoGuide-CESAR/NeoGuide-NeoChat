"""Data models for document ingestion and parsing."""

from pydantic import BaseModel, ConfigDict, Field


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
