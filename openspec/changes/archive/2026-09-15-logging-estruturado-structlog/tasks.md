# Tasks: Logging Estruturado com structlog e Correlação de Requisições

## 1. Especificação OpenSpec
- [x] 1.1 Criar proposta da change `openspec/changes/2026-09-15-logging-estruturado-structlog/proposal.md`.
- [x] 1.2 Criar delta spec `openspec/changes/2026-09-15-logging-estruturado-structlog/specs/system-diagnostics/spec.md`.
- [x] 1.3 Criar design arquitetural `openspec/changes/2026-09-15-logging-estruturado-structlog/design.md`.
- [x] 1.4 Criar checklist de tarefas `openspec/changes/2026-09-15-logging-estruturado-structlog/tasks.md`.

## 2. Desenvolvimento Orientado a Testes (TDD) - Fase Vermelha (RED)
- [x] 2.1 Criar `tests/unit/test_logging.py` com testes para `setup_logging` e renderizadores (JSON para prod/staging, Console para dev).
- [x] 2.2 Adicionar testes unitários para o processador defensivo `redact_sensitive_data` com chaves sensíveis diretas e aninhadas.
- [x] 2.3 Adicionar testes para unificação com logs da stdlib (`uvicorn`, etc.).
- [x] 2.4 Adicionar testes unitários e de integração para `CorrelationIdMiddleware` (geração/propagação de `X-Request-ID`, contextvars e métricas).
- [x] 2.5 Adicionar testes de integração no FastAPI (`main.py`) com headers e logging.
- [x] 2.6 Executar os testes e confirmar falha inicial (Fase Vermelha).

## 3. Desenvolvimento Orientado a Testes (TDD) - Fase Verde (GREEN)
- [x] 3.1 Implementar `src/lumi/core/logging.py` com `setup_logging` e `redact_sensitive_data`.
- [x] 3.2 Implementar `src/lumi/api/middleware.py` com `CorrelationIdMiddleware`.
- [x] 3.3 Atualizar `src/lumi/main.py` para chamar `setup_logging()` e registrar o middleware.
- [x] 3.4 Executar `uv run pytest tests/unit/test_logging.py` e garantir 100% de aprovação (Fase Verde).

## 4. Refatoração, Qualidade e Suíte Completa (REFACTOR)
- [x] 4.1 Executar suíte completa de testes (`uv run pytest`) para garantir não-regressão.
- [x] 4.2 Executar linter `uv run ruff check .` e corrigir apontamentos se houver.
- [x] 4.3 Executar checagem estática de tipos `uv run mypy src/`.

## 5. Sincronização e Arquivamento OpenSpec
- [x] 5.1 Sincronizar delta spec na especificação canônica em `openspec/specs/system-diagnostics/spec.md`.
- [x] 5.2 Mover a change para `openspec/changes/archive/2026-09-15-logging-estruturado-structlog/`.

## 6. Commit Semântico Local
- [x] 6.1 Executar commit semântico local na branch `feat/TECH-05-logging-estruturado-structlog`.
