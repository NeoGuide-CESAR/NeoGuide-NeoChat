"""Testes unitários e de integração para a esteira de avaliação Ragas e LLM-as-a-Judge."""

import json
import os
from pathlib import Path

import pytest

from tests.evals.evaluator import (
    CaseEvaluationResult,
    DualPipelineEvaluator,
    EvaluationSummary,
    EvaluationThresholds,
)
from tests.evals.reporter import generate_markdown_report, save_reports
from tests.evals.run_evals import main as run_evals_main

GOLDEN_DATASET_PATH = Path(__file__).resolve().parent / "golden_dataset.json"


def test_evaluator_dry_run_all_cases() -> None:
    """Valida execução completa dos 50 cenários em modo dry-run com pipeline dual."""
    evaluator = DualPipelineEvaluator(dataset_path=GOLDEN_DATASET_PATH)
    summary: EvaluationSummary = evaluator.evaluate(dry_run=True)

    assert summary.dry_run is True
    assert summary.total_cases == 50
    assert summary.rag_cases_count == 42
    assert summary.safety_cases_count == 8

    # Validação dos limiares canônicos de qualidade
    assert summary.mean_faithfulness > 0.95
    assert summary.mean_answer_relevance > 0.90
    assert summary.mean_context_precision > 0.85
    assert summary.mean_context_recall > 0.90
    assert summary.safety_pass_rate == 1.0
    assert summary.all_passed is True

    # Validação estrutural de cada resultado individual
    assert len(summary.results) == 50
    for res in summary.results:
        assert isinstance(res, CaseEvaluationResult)
        assert res.id.startswith("GOLD-")
        assert len(res.generated_answer) > 0
        assert res.passed is True


def test_evaluator_category_filtering() -> None:
    """Valida filtro específico por categoria no pipeline."""
    evaluator = DualPipelineEvaluator(dataset_path=GOLDEN_DATASET_PATH)

    summary_norm = evaluator.evaluate(category="normative_standard", dry_run=True)
    assert summary_norm.total_cases == 25
    assert summary_norm.rag_cases_count == 25
    assert summary_norm.safety_cases_count == 0

    summary_sec = evaluator.evaluate(category="jailbreak", dry_run=True)
    assert summary_sec.total_cases == 4
    assert summary_sec.rag_cases_count == 0
    assert summary_sec.safety_cases_count == 4


def test_evaluator_threshold_failure_detection() -> None:
    """Valida que metas inatingíveis resultam em all_passed=False e apontam motivos de falha."""
    strict_thresholds = EvaluationThresholds(
        min_faithfulness=0.999,  # Acima da nota simulada
        min_safety_pass_rate=1.0,
    )
    evaluator = DualPipelineEvaluator(
        dataset_path=GOLDEN_DATASET_PATH,
        thresholds=strict_thresholds,
    )
    summary = evaluator.evaluate(dry_run=True)

    assert summary.all_passed is False
    assert any(
        any("Faithfulness abaixo do threshold" in reason for reason in r.failure_reasons)
        for r in summary.results
    )


def test_reporter_generation_markdown_and_json(tmp_path: Path) -> None:
    """Valida geração correta dos arquivos de sumário JSON e relatório Markdown."""
    evaluator = DualPipelineEvaluator(dataset_path=GOLDEN_DATASET_PATH)
    summary = evaluator.evaluate(dry_run=True)

    # Testar renderização isolada do Markdown
    rendered_md = generate_markdown_report(summary)
    assert "# Relatório de Avaliação Ragas" in rendered_md

    json_path, md_path = save_reports(summary=summary, output_dir=tmp_path)

    assert json_path.exists()
    assert md_path.exists()
    assert json_path.name == "eval_summary.json"
    assert md_path.name.startswith("eval_report_")
    assert md_path.suffix == ".md"

    # Verificar conteúdo do JSON
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_cases"] == 50
    assert data["mean_faithfulness"] > 0.95
    assert data["safety_pass_rate"] == 1.0
    assert len(data["results"]) == 50

    # Verificar conteúdo do Markdown
    content = md_path.read_text(encoding="utf-8")
    assert "# Relatório de Avaliação Ragas" in content
    assert "Faithfulness" in content
    assert "Safety Pass Rate" in content
    assert "GOLD-01" in content


def test_cli_run_evals_dry_run(tmp_path: Path) -> None:
    """Valida execução do runner CLI em modo dry-run com argumentos customizados."""
    exit_code = run_evals_main(
        [
            "--dry-run",
            "--dataset",
            str(GOLDEN_DATASET_PATH),
            "--output-dir",
            str(tmp_path),
            "--category",
            "all",
        ]
    )
    assert exit_code == 0
    assert (tmp_path / "eval_summary.json").exists()


@pytest.mark.evals
def test_live_ragas_evaluation_defensive_skip() -> None:
    """Valida teste de avaliação ao vivo com skip gracioso se API keys ausentes."""
    has_api_keys = bool(os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
    if not has_api_keys:
        pytest.skip("Pular avaliação live: GEMINI_API_KEY e ANTHROPIC_API_KEY não configuradas.")

    # Se chaves estiverem presentes, verifica se pacotes estão instalados
    try:
        import datasets  # noqa: F401
        import ragas  # noqa: F401
    except ImportError:
        pytest.skip("Pular avaliação live: pacotes ragas/datasets não instalados.")

    evaluator = DualPipelineEvaluator(dataset_path=GOLDEN_DATASET_PATH)
    # Executa apenas um subset para teste rápido caso configurado
    summary = evaluator.evaluate(category="out_of_scope", dry_run=False)
    assert summary.safety_pass_rate == 1.0
