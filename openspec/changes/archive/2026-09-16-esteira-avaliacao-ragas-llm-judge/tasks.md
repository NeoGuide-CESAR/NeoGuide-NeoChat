# Tasks: Esteira Automatizada de Avaliação Ragas com LLM-as-a-Judge

## Checklist de Implementação

- [x] 1. Especificações e Planejamento SDD
  - [x] 1.1 Criar proposta da change em `openspec/changes/2026-09-16-esteira-avaliacao-ragas-llm-judge/proposal.md`
  - [x] 1.2 Criar delta spec em `openspec/changes/2026-09-16-esteira-avaliacao-ragas-llm-judge/specs/evals-ragas-pipeline/spec.md`
  - [x] 1.3 Criar documento de design em `openspec/changes/2026-09-16-esteira-avaliacao-ragas-llm-judge/design.md`
  - [x] 1.4 Estruturar checklist em `openspec/changes/2026-09-16-esteira-avaliacao-ragas-llm-judge/tasks.md`

- [x] 2. Configuração de Dependências e Pytest
  - [x] 2.1 Adicionar grupo opcional `evals` em `pyproject.toml` (`ragas>=0.2.0`, `datasets>=2.20.0`)
  - [x] 2.2 Registrar marker `evals` em `pyproject.toml`
  - [x] 2.3 Adicionar `pythonpath = ["src"]` em `[tool.pytest.ini_options]`

- [x] 3. Fase Red do TDD
  - [x] 3.1 Criar testes unitários em `tests/evals/test_rag_evals.py` testando evaluator, thresholds, reporter e CLI runner
  - [x] 3.2 Executar `pytest tests/evals/test_rag_evals.py` e certificar falha esperada (Red)

- [x] 4. Fase Green do TDD
  - [x] 4.1 Implementar `tests/evals/evaluator.py` com pipeline dual, classes de resultado, cálculo de métricas e modo dry-run
  - [x] 4.2 Implementar `tests/evals/reporter.py` com gerador de Markdown e JSON em `tests/evals/results/`
  - [x] 4.3 Implementar `tests/evals/run_evals.py` com suporte a CLI args (`--dry-run`, `--dataset`, `--output-dir`, `--category`)
  - [x] 4.4 Executar `pytest tests/evals/test_rag_evals.py` e certificar 100% de aprovação (Green)

- [x] 5. Fase Refactor & Documentação & Qualidade
  - [x] 5.1 Atualizar Seção 4.2 de `docs/07-SEGURANCA-E-AVALIACAO-IA.md` com comandos e exemplos de relatórios
  - [x] 5.2 Executar `ruff check src/ tests/` e corrigir problemas
  - [x] 5.3 Executar `mypy src/lumi` e validar conformidade de tipagem
  - [x] 5.4 Executar suite de testes em `tests/evals/`

- [x] 6. Sincronização e Arquivamento OpenSpec
  - [x] 6.1 Criar especificação canônica em `openspec/specs/evals-ragas-pipeline/spec.md`
  - [x] 6.2 Mover a change para `openspec/changes/archive/2026-09-16-esteira-avaliacao-ragas-llm-judge/`
  - [x] 6.3 Marcar todas as tarefas como concluídas em `tasks.md`

- [x] 7. Commit Semântico Local
  - [x] 7.1 Executar `git add .`
  - [x] 7.2 Executar `git commit -m "tech(TECH-07): esteira automatizada de avaliacao ragas com llm-as-a-judge"`
