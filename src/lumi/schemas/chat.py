"""Schemas Pydantic para contratos da API de Chat e Eventos SSE."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class SourceMetadata(BaseModel):
    """Metadados estruturados de uma fonte normativa citada em respostas RAG."""

    model_config = ConfigDict(extra="ignore")

    document_code: str = Field(
        ...,
        min_length=1,
        description="Código oficial da norma técnica (ex.: DIS-NOR-030)",
    )
    revision: str = Field(
        default="",
        description="Identificador de revisão da norma (ex.: REV07)",
    )
    section: str = Field(
        ...,
        min_length=1,
        description="Seção, capítulo ou tabela referenciada (ex.: Item 5.3)",
    )
    page: int = Field(
        ...,
        ge=1,
        description="Número da página no documento original (>= 1)",
    )
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score de similaridade ou relevância no intervalo [0.0, 1.0]",
    )
    snippet: str = Field(
        default="",
        description="Trecho textual relevante extraído da norma",
    )
    audit_flags: list[str] = Field(
        default_factory=list,
        description="Flags de auditoria de guardrails de saída",
    )


class ChatRequest(BaseModel):
    """Payload de requisição para envio de mensagem no endpoint /api/v1/chat."""

    model_config = ConfigDict(extra="ignore")

    session_id: UUID = Field(
        ...,
        description="Identificador único UUID da sessão de conversa",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Pergunta ou mensagem do usuário",
    )
    stream: bool = Field(
        default=True,
        description="Indica se a resposta deve ser transmitida em tempo real via SSE",
    )

    @field_validator("message")
    @classmethod
    def validate_message_not_blank(cls, v: str) -> str:
        """Garante que a mensagem não seja vazia nem composta apenas por espaços."""
        if not v.strip():
            raise ValueError("A mensagem não pode ser vazia ou conter apenas espaços em branco.")
        return v.strip()


class ChatResponse(BaseModel):
    """Payload de resposta síncrona (stream=False) do endpoint /api/v1/chat."""

    model_config = ConfigDict(extra="ignore")

    session_id: UUID = Field(
        ...,
        description="Identificador único da sessão de chat",
    )
    response: str = Field(
        ...,
        description="Texto completo da resposta elaborada pelo assistente",
    )
    sources: list[SourceMetadata] = Field(
        default_factory=list,
        description="Lista estruturada de fontes normativas que embasam a resposta",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC de criação da resposta",
    )


class StreamTokenEvent(BaseModel):
    """Evento SSE de emissão de token incremental durante geração do LLM."""

    model_config = ConfigDict(extra="ignore")

    token: str = Field(
        ...,
        description="Fragmento de texto gerado incrementalmente pelo modelo",
    )


class StreamSourcesEvent(BaseModel):
    """Evento SSE contendo o catálogo consolidado de fontes citadas."""

    model_config = ConfigDict(extra="ignore")

    sources: list[SourceMetadata] = Field(
        default_factory=list,
        description="Lista de fontes normativas referenciadas na resposta",
    )


class StreamDoneEvent(BaseModel):
    """Evento SSE indicando o encerramento com sucesso do fluxo de streaming."""

    model_config = ConfigDict(extra="ignore")

    session_id: UUID = Field(
        ...,
        description="Identificador da sessão finalizada",
    )


class StreamErrorEvent(BaseModel):
    """Evento SSE emitido em situações de erro durante o streaming da resposta."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    error: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("error", "message"),
        description="Mensagem descritiva e amigável do erro",
    )
    code: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("code", "error_code"),
        description="Código identificador do erro (ex.: LLM_STREAM_ERROR)",
    )
