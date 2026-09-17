"""Testes de integridade estrutural e tipagem do Golden Dataset de Evals."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from lumi.rag.guardrails import INJECTION_REJECTION_REASON, SCOPE_REJECTION_REASON
from lumi.schemas.evals import (
    DatasetCategory,
    ExpectedBehavior,
    GoldenDataset,
    GoldenDatasetItem,
)

GOLDEN_DATASET_PATH = Path(__file__).resolve().parent.parent / "evals" / "golden_dataset.json"


def test_golden_dataset_file_exists() -> None:
    """Valida se o arquivo tests/evals/golden_dataset.json existe e é legível."""
    assert GOLDEN_DATASET_PATH.exists(), f"Arquivo não encontrado: {GOLDEN_DATASET_PATH}"
    assert GOLDEN_DATASET_PATH.is_file()


def test_golden_dataset_pydantic_validation() -> None:
    """Valida o carregamento e parsing integral do dataset pelo modelo GoldenDataset."""
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)

    dataset = GoldenDataset.model_validate(data)
    assert dataset.version is not None
    assert len(dataset.items) == 50


def test_golden_dataset_item_count_and_distribution() -> None:
    """Valida a contagem total de 50 itens e a distribuição exata entre categorias."""
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)

    dataset = GoldenDataset.model_validate(data)
    items = dataset.items

    assert len(items) == 50, f"Esperado exatamente 50 itens, encontrado {len(items)}"

    counts: dict[str, int] = {}
    for item in items:
        counts[item.category.value] = counts.get(item.category.value, 0) + 1

    assert counts.get(DatasetCategory.NORMATIVE_STANDARD.value, 0) == 25
    assert counts.get(DatasetCategory.EDGE_CASE.value, 0) == 12
    assert counts.get(DatasetCategory.NORM_CONFLICT.value, 0) == 5
    assert counts.get(DatasetCategory.OUT_OF_SCOPE.value, 0) == 4
    assert counts.get(DatasetCategory.JAILBREAK.value, 0) == 4


def test_golden_dataset_ids_uniqueness_and_format() -> None:
    """Valida formato sequencial GOLD-01 a GOLD-50 e unicidade estrita dos identificadores."""
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)

    dataset = GoldenDataset.model_validate(data)
    expected_ids = [f"GOLD-{i:02d}" for i in range(1, 51)]
    actual_ids = [item.id for item in dataset.items]

    assert actual_ids == expected_ids
    assert len(set(actual_ids)) == 50


def test_golden_dataset_security_ground_truths() -> None:
    """Valida se casos out_of_scope e jailbreak utilizam as mensagens canônicas de guardrails."""
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)

    dataset = GoldenDataset.model_validate(data)

    for item in dataset.items:
        if item.category == DatasetCategory.OUT_OF_SCOPE:
            assert item.expected_behavior == ExpectedBehavior.SCOPE_REFUSAL
            assert item.ground_truth_answer == SCOPE_REJECTION_REASON
        elif item.category == DatasetCategory.JAILBREAK:
            assert item.expected_behavior == ExpectedBehavior.INJECTION_REFUSAL
            assert item.ground_truth_answer == INJECTION_REJECTION_REASON


def test_golden_dataset_normative_sources() -> None:
    """Valida se casos normativos possuem fontes e seções esperadas preenchidas."""
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)

    dataset = GoldenDataset.model_validate(data)

    normative_categories = {
        DatasetCategory.NORMATIVE_STANDARD,
        DatasetCategory.EDGE_CASE,
        DatasetCategory.NORM_CONFLICT,
    }

    for item in dataset.items:
        if item.category in normative_categories:
            assert len(item.expected_sources) > 0, f"Item {item.id} deve ter expected_sources"
            assert len(item.expected_sections) > 0, f"Item {item.id} deve ter expected_sections"
            assert item.expected_behavior == ExpectedBehavior.GROUNDED_ANSWER
            for src in item.expected_sources:
                assert src in {"DIS-NOR-030", "DIS-NOR-053", "DIS-NOR-030 / DIS-NOR-053"}


def test_golden_dataset_schema_rejects_duplicates() -> None:
    """Valida que o schema GoldenDataset acusa erro se houver IDs duplicados."""
    item1 = GoldenDatasetItem(
        id="GOLD-01",
        category=DatasetCategory.NORMATIVE_STANDARD,
        question="Pergunta de teste 1 com tamanho adequado?",
        ground_truth_answer="Resposta técnica válida com fundamentação normativa completa.",
        expected_behavior=ExpectedBehavior.GROUNDED_ANSWER,
        expected_sources=["DIS-NOR-030"],
        expected_sections=["5.3"],
        description="Descrição de teste do item 1",
    )
    item2 = GoldenDatasetItem(
        id="GOLD-01",
        category=DatasetCategory.NORMATIVE_STANDARD,
        question="Pergunta de teste 2 com tamanho adequado?",
        ground_truth_answer="Resposta técnica válida com fundamentação normativa completa.",
        expected_behavior=ExpectedBehavior.GROUNDED_ANSWER,
        expected_sources=["DIS-NOR-030"],
        expected_sections=["5.3"],
        description="Descrição de teste do item 2",
    )

    with pytest.raises(ValidationError, match="Identificadores duplicados"):
        GoldenDataset(
            version="1.0.0",
            description="Dataset de teste com duplicatas",
            items=[item1, item2],
        )
