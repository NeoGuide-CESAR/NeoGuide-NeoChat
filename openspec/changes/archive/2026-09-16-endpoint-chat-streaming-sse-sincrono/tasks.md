# Tasks: Endpoint de Chat com Streaming SSE e Fallback Síncrono

## 1. Especificação OpenSpec
- [x] 1.1 Criar proposta da change `openspec/changes/2026-09-16-endpoint-chat-streaming-sse-sincrono/proposal.md`.
- [x] 1.2 Criar delta spec `openspec/changes/2026-09-16-endpoint-chat-streaming-sse-sincrono/specs/chat-streaming-api/spec.md`.
- [x] 1.3 Criar design de arquitetura `openspec/changes/2026-09-16-endpoint-chat-streaming-sse-sincrono/design.md`.
- [x] 1.4 Criar checklist de tarefas `openspec/changes/2026-09-16-endpoint-chat-streaming-sse-sincrono/tasks.md`.

## 2. Fase RED do TDD (Testes Falhando)
- [x] 2.1 Criar testes unitários em `tests/unit/test_chat_service.py`:
  - `stream_chat` com guardrail violado (bloqueio de injection/escopo emitindo recusa e sources=[])
  - `stream_chat` com resposta de contingência do RAG (emissão de CONTINGENCY_NO_SOURCES_MESSAGE, sources=[], done)
  - `stream_chat` com fluxo padrão LLM (emissão de eventos token, sources e done)
  - `stream_chat` com erro na geração LLM (emissão de evento error com LLM_STREAM_ERROR)
  - `process_chat` síncrono retornando `ChatResponse` estruturado
  - Persistência das mensagens de usuário e assistente via `session_service`
- [x] 2.2 Criar testes de integração em `tests/integration/test_chat_api.py`:
  - POST `/api/v1/chat` com `stream=true` retornando StreamingResponse `text/event-stream` com headers apropriados
  - POST `/api/v1/chat` com `stream=false` retornando 200 OK com `ChatResponse` JSON
  - POST `/api/v1/chat` com `session_id` inexistente retornando 404 Not Found
  - POST `/api/v1/chat` com sessão expirada por TTL retornando 410 Gone
  - POST `/api/v1/chat` sem API Key ou inválida retornando 401 Unauthorized
- [x] 2.3 Executar testes e confirmar falhas esperadas (Fase RED).

## 3. Fase GREEN do TDD (Implementação)
- [x] 3.1 Implementar `ChatService` em `src/lumi/services/chat_service.py` com `stream_chat`, `process_chat` e formatação SSE.
- [x] 3.2 Exportar `ChatService` em `src/lumi/services/__init__.py`.
- [x] 3.3 Implementar endpoint `POST /api/v1/chat` em `src/lumi/api/v1/chat.py`.
- [x] 3.4 Registrar roteador de chat em `src/lumi/api/v1/router.py`.
- [x] 3.5 Executar testes unitários e de integração até aprovação de 100% (Fase GREEN).

## 4. Fase REFACTOR & Qualidade
- [x] 4.1 Executar linter `uv run ruff check src/ tests/`.
- [x] 4.2 Executar checagem estática de tipos `uv run mypy src/lumi`.
- [x] 4.3 Executar suíte completa de testes `uv run pytest`.

## 5. Sincronização e Arquivamento OpenSpec
- [x] 5.1 Mesclar especificação canônica em `openspec/specs/chat-streaming-api/spec.md`.
- [x] 5.2 Mover a pasta da change para `openspec/changes/archive/2026-09-16-endpoint-chat-streaming-sse-sincrono/`.
- [x] 5.3 Marcar todas as tarefas como concluídas em `tasks.md`.

## 6. Commit Semântico Local
- [x] 6.1 Executar commit semântico local na worktree sem realizar push.
