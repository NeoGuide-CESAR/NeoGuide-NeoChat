# Tasks: Gerenciamento de Sessões, Histórico Multi-turn e TTL

## 1. Especificação OpenSpec
- [x] 1.1 Criar proposta da change `openspec/changes/2026-09-16-gestao-sessoes-historico-multi-turn-ttl/proposal.md`.
- [x] 1.2 Criar delta spec `openspec/changes/2026-09-16-gestao-sessoes-historico-multi-turn-ttl/specs/session-management/spec.md`.
- [x] 1.3 Criar design de arquitetura `openspec/changes/2026-09-16-gestao-sessoes-historico-multi-turn-ttl/design.md`.
- [x] 1.4 Criar checklist de tarefas `openspec/changes/2026-09-16-gestao-sessoes-historico-multi-turn-ttl/tasks.md`.

## 2. Fase RED do TDD (Testes Falhando)
- [x] 2.1 Criar testes unitários em `tests/unit/test_session_service.py` cobrindo:
  - Criação de sessão (`create_session`) e unicidade de IDs
  - `get_session` e `get_session_or_raise`
  - Inserção de mensagens (`add_message`) e atualização de `updated_at`
  - Consulta de histórico ordenado (`get_history`) com limite
  - Conversão para mensagens LangChain (`get_langchain_messages`) retornando `HumanMessage`, `AIMessage`, `SystemMessage`
  - Expiração por inatividade TTL levantando `SessionExpiredError`
  - Busca de sessão inexistente levantando `SessionNotFoundError`
- [x] 2.2 Criar testes de integração em `tests/integration/test_sessions_api.py` cobrindo:
  - POST `/api/v1/sessions` (201 Created retornando `SessionCreateResponse`)
  - GET `/api/v1/sessions/{session_id}` (200 OK retornando `SessionDetailResponse` com histórico)
  - GET `/api/v1/sessions/{session_id}` com ID inexistente retornando 404
  - GET `/api/v1/sessions/{session_id}` com sessão expirada retornando 410 Gone
  - Proteção por X-API-Key inválida ou ausente (401/403)
- [x] 2.3 Executar os testes e confirmar que falham (Fase RED).

## 3. Fase GREEN do TDD (Implementação)
- [x] 3.1 Ajustar configurações em `src/lumi/core/config.py` (`session_ttl_hours = 1`, `chat_history_limit = 10`).
- [x] 3.2 Implementar exceções e `SessionService` em `src/lumi/services/session_service.py`.
- [x] 3.3 Exportar `SessionService` e exceções em `src/lumi/services/__init__.py`.
- [x] 3.4 Implementar roteador `src/lumi/api/v1/sessions.py` com rotas POST e GET.
- [x] 3.5 Registrar `sessions_router` em `src/lumi/api/v1/router.py`.
- [x] 3.6 Executar testes unitários e de integração até que 100% passem (Fase GREEN).

## 4. Fase REFACTOR & Qualidade
- [x] 4.1 Executar linter `uv run ruff check src/ tests/`.
- [x] 4.2 Executar checagem de tipos estáticos `uv run mypy src/lumi`.
- [x] 4.3 Executar a suíte completa de testes `uv run pytest`.

## 5. Sincronização e Arquivamento OpenSpec
- [x] 5.1 Mesclar especificação canônica em `openspec/specs/session-management/spec.md`.
- [x] 5.2 Mover a pasta da change para `openspec/changes/archive/2026-09-16-gestao-sessoes-historico-multi-turn-ttl/`.
- [x] 5.3 Marcar todas as caixas de tarefas como concluídas em `tasks.md`.

## 6. Commit Semântico Local
- [x] 6.1 Executar commit semântico local na worktree sem realizar push.
