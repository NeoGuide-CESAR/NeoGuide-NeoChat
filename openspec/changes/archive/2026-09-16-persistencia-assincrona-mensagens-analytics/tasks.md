# Tasks: Persistência Desacoplada Assíncrona de Mensagens e Telemetria Analítica

- [x] 1. Implementar `AnalyticsService` e `persist_interaction_background` em `src/lumi/services/analytics_service.py` <!-- id: 1 -->
  - [x] 1.1 Criar classe `AnalyticsService` com método `record_query_analytics`
  - [x] 1.2 Implementar rotina assíncrona `persist_interaction_background` com sessão independente via `get_db_session()`
  - [x] 1.3 Adicionar lógica de retentativa (1 retry com 500ms backoff) e logs estruturados `structlog`
- [x] 2. Integrar persistência assíncrona no `ChatService` e API de chat <!-- id: 2 -->
  - [x] 2.1 Atualizar `stream_chat` em `src/lumi/services/chat_service.py` para despacho em background pós-evento `done`
  - [x] 2.2 Atualizar `process_chat` para suportar agendamento via `BackgroundTasks`
  - [x] 2.3 Atualizar endpoint `POST /api/v1/chat` em `src/lumi/api/v1/chat.py` injetando `BackgroundTasks`
  - [x] 2.4 Cobrir cenários de RAG sucesso, contingência e recusa de guardrails
- [x] 3. Implementar testes unitários e de integração <!-- id: 3 -->
  - [x] 3.1 Criar testes unitários em `tests/unit/test_analytics_service.py` (sucesso, retentativa, falha total silenciada)
  - [x] 3.2 Atualizar `tests/unit/test_chat_service.py` para validar despacho desacoplado
  - [x] 3.3 Criar testes de integração em `tests/integration/test_chat_background_persistence.py`
- [x] 4. Verificação de qualidade estrita e sincronização OpenSpec <!-- id: 4 -->
  - [x] 4.1 Executar `pytest`, `ruff check` e `mypy` garantindo 100% de sucesso
  - [x] 4.2 Sincronizar delta spec em `openspec/specs/chat-streaming-api/spec.md`
  - [x] 4.3 Arquivar change em `openspec/changes/archive/`
  - [x] 4.4 Realizar commit git padronizado na branch da worktree
