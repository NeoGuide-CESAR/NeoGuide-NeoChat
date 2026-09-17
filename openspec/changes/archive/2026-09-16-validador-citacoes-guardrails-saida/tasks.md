# Tasks: Validador Assíncrono de Citações e Guardrails de Saída via BackgroundTasks

## Implementation Tasks

- [x] 1. Especificação de Testes Unitários dos Guardrails de Saída <!-- id: 1-unit-tests-output-guardrails -->
  - [x] 1.1 Criar `tests/unit/test_output_guardrails.py` cobrindo cenários de extração de citações (única, múltipla, com paginação, sem citação).
  - [x] 1.2 Cobrir cenários de salvaguarda de cálculo (cálculo sem Wizard, cálculo com Wizard, sem cálculo).
  - [x] 1.3 Cobrir validação cruzada com fragmentos recuperados (citações legítimas, seções alucinadas, normas alucinadas, contexto vazio).

- [x] 2. Implementação do Módulo de Guardrails de Saída <!-- id: 2-implement-output-guardrails -->
  - [x] 2.1 Criar dataclass `OutputGuardrailResult` em `src/lumi/rag/output_guardrails.py`.
  - [x] 2.2 Implementar `extract_citations(text: str) -> list[tuple[str, str]]`.
  - [x] 2.3 Implementar `check_calculation_safeguard(text: str) -> bool`.
  - [x] 2.4 Implementar `validate_output(response_text: str, retrieved_chunks: list[RetrievedChunk] | list[dict[str, Any]] | None) -> OutputGuardrailResult`.
  - [x] 2.5 Exportar estruturas e funções em `src/lumi/rag/__init__.py`.

- [x] 3. Integração com Worker Assíncrono e Auditoria <!-- id: 3-integration-analytics-service -->
  - [x] 3.1 Atualizar `persist_interaction_background` em `src/lumi/services/analytics_service.py` para invocar `validate_output`.
  - [x] 3.2 Emitir log estruturado `logger.warning("output_guardrail_violation", ...)` em violações.
  - [x] 3.3 Gravar `audit_flags` nos metadados de `ChatMessage.sources` persistidos.
  - [x] 3.4 Conectar `retrieved_chunks` no despacho de persistência em `src/lumi/services/chat_service.py`.

- [x] 4. Testes de Integração e Verificação de Qualidade <!-- id: 4-integration-tests-and-qa -->
  - [x] 4.1 Criar `tests/integration/test_output_audit_background.py` testando fluxo completo assíncrono pós-chat com emissão de warning e persistência de flags.
  - [x] 4.2 Executar suíte completa do pytest (`pytest.exe`).
  - [x] 4.3 Executar checagem de linter e formatação (`ruff.exe check src/ tests/`).
  - [x] 4.4 Executar checagem de tipos (`mypy.exe src/lumi`).

- [x] 5. Sincronização Canônica e Arquivamento OpenSpec <!-- id: 5-sync-and-archive -->
  - [x] 5.1 Criar especificação canônica em `openspec/specs/output-guardrails/spec.md`.
  - [x] 5.2 Mover a change para `openspec/changes/archive/2026-09-16-validador-citacoes-guardrails-saida`.
