"""Gerador de relatórios executivos em Markdown e JSON para a esteira de Evals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.evals.evaluator import EvaluationSummary

DEFAULT_RESULTS_DIR = Path(__file__).resolve().parent / "results"


def generate_markdown_report(summary: EvaluationSummary) -> str:
    """Gera relatório formatado em Markdown com tabelas GFM e análise de conformidade."""
    overall_status = "✅ APROVADO" if summary.all_passed else "❌ REPROVADO"
    mode_str = "Simulado (Dry-Run)" if summary.dry_run else "Execução Real (Live LLM/Ragas)"

    faith_status = "✅" if summary.mean_faithfulness >= summary.thresholds.min_faithfulness else "❌"
    rel_status = "✅" if summary.mean_answer_relevance >= summary.thresholds.min_answer_relevance else "❌"
    prec_status = "✅" if summary.mean_context_precision >= summary.thresholds.min_context_precision else "❌"
    rec_status = "✅" if summary.mean_context_recall >= summary.thresholds.min_context_recall else "❌"
    safe_status = "✅" if summary.safety_pass_rate >= summary.thresholds.min_safety_pass_rate else "❌"

    lines: list[str] = [
        "# Relatório de Avaliação Ragas com LLM-as-a-Judge — Lumi NeoGuide",
        "",
        f"**Status Geral:** {overall_status}  ",
        f"**Data/Hora (UTC):** `{summary.timestamp}`  ",
        f"**Modo de Execução:** {mode_str}  ",
        f"**Total de Casos Avaliados:** {summary.total_cases} (RAG: {summary.rag_cases_count}, Segurança: {summary.safety_cases_count})",
        "",
        "---",
        "",
        "## 1. Sumário Executivo de Métricas Globais",
        "",
        "| Métrica | Meta / Limiar Mínimo | Valor Obtido | Status |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Faithfulness (Fidelidade)** | > {summary.thresholds.min_faithfulness:.2f} | {summary.mean_faithfulness:.4f} | {faith_status} |",
        f"| **Answer Relevance (Relevância)** | > {summary.thresholds.min_answer_relevance:.2f} | {summary.mean_answer_relevance:.4f} | {rel_status} |",
        f"| **Context Precision (Precisão)** | > {summary.thresholds.min_context_precision:.2f} | {summary.mean_context_precision:.4f} | {prec_status} |",
        f"| **Context Recall (Cobertura)** | > {summary.thresholds.min_context_recall:.2f} | {summary.mean_context_recall:.4f} | {rec_status} |",
        f"| **Safety Pass Rate (Segurança)** | = {summary.thresholds.min_safety_pass_rate:.2f} | {summary.safety_pass_rate:.4f} | {safe_status} |",
        "",
        "---",
        "",
        "## 2. Detalhamento dos Cenários de Teste",
        "",
        "| ID | Categoria | Comportamento Esperado | Status | Notas / Observações |",
        "| :--- | :--- | :--- | :---: | :--- |",
    ]

    for res in summary.results:
        res_status = "✅ PASS" if res.passed else "❌ FAIL"
        if res.is_safe is not None and (res.category in {"out_of_scope", "jailbreak"}):
            notes = "Guardrail canônico acionado" if res.is_safe else "Falha de bloqueio"
        else:
            notes = (
                f"F:{res.faithfulness:.2f} R:{res.answer_relevance:.2f} "
                f"P:{res.context_precision:.2f} Rec:{res.context_recall:.2f}"
                if res.faithfulness is not None
                else "-"
            )
        if res.failure_reasons:
            notes += f" (Alertas: {'; '.join(res.failure_reasons)})"

        lines.append(
            f"| `{res.id}` | `{res.category}` | `{res.expected_behavior}` | {res_status} | {notes} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "> Relatório gerado automaticamente pela esteira de avaliação contínua da Lumi (NeoGuide).",
        "",
    ])

    return "\n".join(lines)


def save_reports(
    summary: EvaluationSummary,
    output_dir: Path | str = DEFAULT_RESULTS_DIR,
) -> tuple[Path, Path]:
    """Salva os relatórios JSON e Markdown no diretório de resultados especificado.

    Args:
        summary: Objeto EvaluationSummary consolidado.
        output_dir: Diretório de destino dos arquivos.

    Returns:
        tuple[Path, Path]: Tupla contendo os caminhos do (json_path, md_path) gerados.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    json_path = out_path / "eval_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)

    md_filename = f"eval_report_{summary.timestamp}.md"
    md_path = out_path / md_filename
    md_content = generate_markdown_report(summary)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return json_path, md_path
