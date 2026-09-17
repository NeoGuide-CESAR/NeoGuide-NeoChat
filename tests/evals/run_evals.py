"""Script CLI runner para execução da esteira automatizada de avaliação Ragas."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Garante resolução do pacote src/lumi mesmo em worktrees isoladas
_src_path = Path(__file__).resolve().parent.parent.parent / "src"
if _src_path.exists() and str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from tests.evals.evaluator import (  # noqa: E402
    DEFAULT_DATASET_PATH,
    DualPipelineEvaluator,
    EvaluationThresholds,
)
from tests.evals.reporter import DEFAULT_RESULTS_DIR, save_reports  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        prog="python -m tests.evals.run_evals",
        description="Executa a esteira de avaliação de RAG e Guardrails do Lumi NeoGuide.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Executa em modo determinístico/mock sem realizar chamadas externas a LLMs.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help=f"Caminho para o arquivo do Golden Dataset (padrão: {DEFAULT_DATASET_PATH}).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help=f"Diretório para gravação dos relatórios gerados (padrão: {DEFAULT_RESULTS_DIR}).",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="all",
        choices=[
            "all",
            "normative_standard",
            "edge_case",
            "norm_conflict",
            "out_of_scope",
            "jailbreak",
        ],
        help="Filtra a avaliação por categoria específica (padrão: 'all').",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada do CLI de avaliação."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = build_parser()
    args = parser.parse_args(argv)

    print("=================================================================")
    print("[LUMI] Lumi NeoGuide - Esteira de Avaliacao Ragas & LLM-as-a-Judge")
    print("=================================================================")
    print(f"[DATASET] Arquivo: {args.dataset}")
    print(f"[FILTRO]  Categoria: {args.category}")
    print(f"[MODO]    {'DRY-RUN (Simulado)' if args.dry_run else 'LIVE (Chamadas Reais)'}")
    print(f"[SAIDA]   Diretório: {args.output_dir}")
    print("-----------------------------------------------------------------")

    evaluator = DualPipelineEvaluator(
        dataset_path=args.dataset,
        thresholds=EvaluationThresholds(),
    )

    try:
        summary = evaluator.evaluate(
            category=args.category,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"\n[ERRO] Falha durante execução da avaliação: {exc}")
        return 1

    json_path, md_path = save_reports(summary, output_dir=args.output_dir)

    print("\n[RESULTADOS] Métricas Consolidadas:")
    print(f"   * Total de Casos: {summary.total_cases}")
    print(f"   * Faithfulness: {summary.mean_faithfulness:.4f} (Meta > {summary.thresholds.min_faithfulness})")
    print(f"   * Answer Relevance: {summary.mean_answer_relevance:.4f} (Meta > {summary.thresholds.min_answer_relevance})")
    print(f"   * Context Precision: {summary.mean_context_precision:.4f} (Meta > {summary.thresholds.min_context_precision})")
    print(f"   * Context Recall: {summary.mean_context_recall:.4f} (Meta > {summary.thresholds.min_context_recall})")
    print(f"   * Safety Pass Rate: {summary.safety_pass_rate:.4f} (Meta = {summary.thresholds.min_safety_pass_rate})")
    print("-----------------------------------------------------------------")
    print(f"[ARQUIVO] JSON salvo em: {json_path}")
    print(f"[ARQUIVO] Markdown salvo em: {md_path}")
    print("-----------------------------------------------------------------")

    if summary.all_passed:
        print("[SUCESSO] Todos os critérios de qualidade e segurança foram aprovados!\n")
        return 0
    else:
        print("[REPROVADO] Uma ou mais métricas não atingiram os limiares mínimos estipulados.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
