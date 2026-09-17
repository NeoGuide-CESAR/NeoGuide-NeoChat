"""Schemas Pydantic para validação do Golden Dataset de Evals do Lumi NeoGuide."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DatasetCategory(StrEnum):
    """Categorias taxionômicas de avaliação do pipeline RAG."""

    NORMATIVE_STANDARD = "normative_standard"
    EDGE_CASE = "edge_case"
    NORM_CONFLICT = "norm_conflict"
    OUT_OF_SCOPE = "out_of_scope"
    JAILBREAK = "jailbreak"


class ExpectedBehavior(StrEnum):
    """Comportamentos esperados da Lumi na resposta."""

    GROUNDED_ANSWER = "grounded_answer"
    CONTINGENCY_REFUSAL = "contingency_refusal"
    SCOPE_REFUSAL = "scope_refusal"
    INJECTION_REFUSAL = "injection_refusal"


class GoldenDatasetItem(BaseModel):
    """Representação estruturada de um cenário normativo de avaliação."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(
        ...,
        pattern=r"^GOLD-\d{2}$",
        description="Identificador único formatado como GOLD-01 a GOLD-50",
    )
    category: DatasetCategory = Field(
        ...,
        description="Categoria analítica do cenário",
    )
    question: str = Field(
        ...,
        min_length=5,
        description="Pergunta formulada pelo projetista ou usuário",
    )
    ground_truth_answer: str = Field(
        ...,
        min_length=10,
        description="Resposta esperada oficial e fundamentada tecnicamente",
    )
    expected_behavior: ExpectedBehavior = Field(
        default=ExpectedBehavior.GROUNDED_ANSWER,
        description="Comportamento esperado da Lumi (resposta fundamentada ou recusa)",
    )
    expected_sources: list[str] = Field(
        default_factory=list,
        description="Normas técnicas oficiais que devem fundamentar a resposta",
    )
    expected_sections: list[str] = Field(
        default_factory=list,
        description="Seções, itens ou tabelas normativas pertinentes",
    )
    description: str = Field(
        ...,
        min_length=5,
        description="Explicação sucinta do propósito do teste e aspectos validados",
    )


class GoldenDataset(BaseModel):
    """Catálogo completo de cenários de avaliação de RAG."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(
        default="1.0.0",
        description="Versão semântica do Golden Dataset",
    )
    description: str = Field(
        ...,
        description="Descrição geral da suíte de avaliação",
    )
    items: list[GoldenDatasetItem] = Field(
        ...,
        min_length=1,
        description="Lista de cenários de avaliação",
    )

    @field_validator("items")
    @classmethod
    def validate_unique_ids(cls, v: list[GoldenDatasetItem]) -> list[GoldenDatasetItem]:
        """Garante que não existem identificadores duplicados na coleção."""
        ids = [item.id for item in v]
        if len(ids) != len(set(ids)):
            duplicates = [x for x in ids if ids.count(x) > 1]
            raise ValueError(f"Identificadores duplicados no Golden Dataset: {set(duplicates)}")
        return v
