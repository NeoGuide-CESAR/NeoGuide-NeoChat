"""Schemas Pydantic para gerenciamento de sessões de chat e histórico."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from lumi.schemas.chat import SourceMetadata


class SessionCreateResponse(BaseModel):
    """Payload de resposta após a criação de uma nova sessão conversacional."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True, extra="ignore")

    id: UUID = Field(
        ...,
        validation_alias=AliasChoices("id", "session_id"),
        description="Identificador único da sessão de chat",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC de criação da sessão",
    )

    @property
    def session_id(self) -> UUID:
        """Propriedade para compatibilidade com clientes que usam session_id."""
        return self.id


class ChatMessageResponse(BaseModel):
    """Representação de uma mensagem individual dentro do histórico de uma sessão."""

    model_config = ConfigDict(extra="ignore")

    id: UUID = Field(
        default_factory=uuid4,
        description="Identificador único da mensagem",
    )
    session_id: UUID = Field(
        ...,
        description="Identificador da sessão vinculada",
    )
    role: Literal["user", "assistant", "system"] = Field(
        ...,
        description="Papel do emissor da mensagem",
    )
    content: str = Field(
        ...,
        description="Conteúdo textual da mensagem",
    )
    sources: list[SourceMetadata] = Field(
        default_factory=list,
        description="Metadados de fontes normativas anexadas (quando aplicável)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC do envio da mensagem",
    )


class SessionDetailResponse(BaseModel):
    """Payload de detalhamento de sessão contendo histórico completo de mensagens."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True, extra="ignore")

    id: UUID = Field(
        ...,
        validation_alias=AliasChoices("id", "session_id"),
        description="Identificador único da sessão de chat",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC de criação da sessão",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp UTC da última interação registrada",
    )
    messages: list[ChatMessageResponse] = Field(
        default_factory=list,
        description="Lista ordenada das mensagens trocadas na sessão",
    )

    @property
    def session_id(self) -> UUID:
        """Propriedade para compatibilidade com clientes que usam session_id."""
        return self.id
