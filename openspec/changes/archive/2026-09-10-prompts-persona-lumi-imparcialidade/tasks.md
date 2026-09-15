# Tasks: Prompts, Persona Lumi e Salvaguarda de Imparcialidade Normativa

## 1. OpenSpec e Especificação
- [x] 1.1 Criar artefatos da change (`proposal.md`, `specs/rag-prompts/spec.md`, `design.md`, `tasks.md`).

## 2. Desenvolvimento Orientado por Testes (TDD)
- [x] 2.1 Fase Red: Criar `tests/unit/test_prompts.py` com testes para persona didática, regras de citação, delegação ao Wizard, imparcialidade normativa, mensagem de contingência e `get_rag_prompt_template()`.
- [x] 2.2 Fase Green: Implementar `src/lumi/rag/prompts.py` e `src/lumi/rag/__init__.py`.
- [x] 2.3 Fase Green: Validar execução de `uv run pytest tests/unit/test_prompts.py` e de toda a suíte de testes.
- [x] 2.4 Fase Refactor: Executar `uv run ruff check .` e `uv run mypy src` corrigindo qualquer pendência.

## 3. Sincronização e Arquivamento OpenSpec
- [x] 3.1 Sincronizar especificação canônica em `openspec/specs/rag-prompts/spec.md`.
- [x] 3.2 Arquivar change em `openspec/changes/archive/2026-09-10-prompts-persona-lumi-imparcialidade/`.
- [x] 3.3 Realizar commit semântico local.
