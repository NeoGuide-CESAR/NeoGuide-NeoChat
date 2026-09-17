# Tasks: Golden Dataset de Avaliação de RAG com 50 Cenários Normativos

## Checklist de Implementação

- [x] 1. Especificações e Planejamento SDD
  - [x] 1.1 Criar proposta da change em `openspec/changes/2026-09-16-golden-dataset-50-cenarios-normativos/proposal.md`
  - [x] 1.2 Criar delta spec em `openspec/changes/2026-09-16-golden-dataset-50-cenarios-normativos/specs/evals-golden-dataset/spec.md`
  - [x] 1.3 Criar documento de design em `openspec/changes/2026-09-16-golden-dataset-50-cenarios-normativos/design.md`
  - [x] 1.4 Estruturar checklist em `openspec/changes/2026-09-16-golden-dataset-50-cenarios-normativos/tasks.md`

- [x] 2. Fase Red do TDD
  - [x] 2.1 Criar `tests/unit/test_golden_dataset.py` cobrindo carregamento, validação Pydantic, contagem exata (50), unicidade dos IDs e respostas de segurança
  - [x] 2.2 Executar `pytest tests/unit/test_golden_dataset.py` e certificar falha esperada (Red)

- [x] 3. Fase Green do TDD
  - [x] 3.1 Implementar `DatasetCategory`, `ExpectedBehavior`, `GoldenDatasetItem` e `GoldenDataset` em `src/lumi/schemas/evals.py`
  - [x] 3.2 Exportar os novos schemas em `src/lumi/schemas/__init__.py`
  - [x] 3.3 Criar diretório `tests/evals/` se necessário
  - [x] 3.4 Construir `tests/evals/golden_dataset.json` com 50 cenários técnicos normativos reais (25 normative_standard, 12 edge_case, 5 norm_conflict, 4 out_of_scope, 4 jailbreak)
  - [x] 3.5 Executar `pytest tests/unit/test_golden_dataset.py` e certificar 100% de aprovação (Green)

- [x] 4. Fase Refactor & Documentação & Qualidade
  - [x] 4.1 Atualizar Seção 4.1 de `docs/07-SEGURANCA-E-AVALIACAO-IA.md` refletindo os schemas e distribuição
  - [x] 4.2 Executar `ruff check src/ tests/` e corrigir problemas
  - [x] 4.3 Executar `mypy src/lumi` e validar tipagem estrita
  - [x] 4.4 Executar suíte completa de testes unitários

- [x] 5. Sincronização e Arquivamento OpenSpec
  - [x] 5.1 Criar especificação canônica em `openspec/specs/evals-golden-dataset/spec.md`
  - [x] 5.2 Mover a change para `openspec/changes/archive/2026-09-16-golden-dataset-50-cenarios-normativos/`
  - [x] 5.3 Marcar todas as tarefas como concluídas em `tasks.md`

- [x] 6. Commit Semântico Local
  - [x] 6.1 Executar `git add .`
  - [x] 6.2 Executar `git commit -m "tech(TECH-06): golden dataset de avaliacao de rag com 50 cenarios normativos"`
