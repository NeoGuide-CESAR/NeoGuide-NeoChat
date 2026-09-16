# Proposal: Endpoint de Chat com Streaming Server-Sent Events (SSE) e Fallback Síncrono

## Context
O Lumi NeoGuide é um assistente normativo inteligente voltado para a consulta, interpretação e aplicação das normas técnicas da Neoenergia Pernambuco (DIS-NOR-030 e DIS-NOR-053).
Para entregar uma experiência de usuário interativa e de baixa latência em conformidade com os requisitos não-funcionais (RNF-01 tempo de resposta, RNF-02 streaming de tokens, RNF-07 tratamento de falhas), a API necessita de um endpoint unificado `POST /api/v1/chat` capaz de transmitir a resposta gerada de forma incremental via Server-Sent Events (SSE) ou, alternativamente, de forma síncrona consolidada (`stream=False`).

## Motivation & Value
1. **Streaming em Tempo Real (RNF-02)**: Redução drástica do Time-To-First-Token (TTFT) perceptível pelo usuário na interface, transmitindo fragmentos de tokens assim que gerados pelo modelo de linguagem.
2. **Protocolo SSE Tipado e Estruturado**: Padronização dos eventos emitidos (`token`, `sources`, `done`, `error`) utilizando schemas Pydantic estritos (`StreamTokenEvent`, `StreamSourcesEvent`, `StreamDoneEvent`, `StreamErrorEvent`), garantindo previsibilidade para clientes frontend e ferramentas de integração.
3. **Orquestração Fim a Fim**: Integração de todas as camadas construídas nas etapas anteriores:
   - Validação de sessão e checagem de TTL de inatividade (RN-05).
   - Guardrails determinísticos de entrada (PII, Prompt Injection e Escopo Temático).
   - Persistência transacional do histórico conversacional (mensagens do usuário e assistente).
   - Contexto RAG integrado (reescrita contextual multi-turn, recuperação vetorial e reranking).
   - Salvaguardas normativas e resposta de contingência imediata (RF-06).
   - Geração de resposta com persona Lumi e temperatura determinística `0.0`.
4. **Resiliência e Fallback Síncrono**: Suporte a clientes que não consomem SSE através de `stream=False` retornando payload JSON `ChatResponse`, e tratamento defensivo de falhas de geração emitindo evento estruturado de erro (`LLM_STREAM_ERROR`).

## Scope

### In-Scope
- Camada de serviço `ChatService` em `src/lumi/services/chat_service.py`:
  - Formatação e emissão de eventos SSE no padrão `event: <tipo>\ndata: <json>\n\n`.
  - Método `stream_chat(request: ChatRequest) -> AsyncGenerator[str, None]`:
    - Validação de sessão e TTL (`SessionNotFoundError` -> 404, `SessionExpiredError` -> 410).
    - Validação de guardrails de entrada via `validate_input`.
    - Persistência de mensagens na sessão via `SessionService`.
    - Recuperação de histórico multi-turn para contexto.
    - Execução da pipeline RAG (`RagContextOrchestrator`).
    - Resposta de contingência rápida (`CONTINGENCY_NO_SOURCES_MESSAGE`).
    - Geração streaming via `llm.astream()` com `temperature=0.0`.
    - Emissão de eventos ordenados: `token` -> `sources` -> `done` (ou `error`).
  - Método `process_chat(request: ChatRequest) -> ChatResponse`:
    - Fluxo idêntico ao de streaming em execução síncrona retornando `ChatResponse`.
- Exportação de `ChatService` em `src/lumi/services/__init__.py`.
- Camada de API REST em `src/lumi/api/v1/chat.py`:
  - Rota `POST /api/v1/chat` protegida por autenticação (`api_key_and_rate_limit`) e injeção de sessão do banco (`get_db_session`).
  - Retorno condicional: `StreamingResponse(media_type="text/event-stream")` se `stream=True`, ou `ChatResponse` (HTTP 200) se `stream=False`.
  - Registro no roteador central `src/lumi/api/v1/router.py`.
- Testes unitários abrangentes em `tests/unit/test_chat_service.py` e testes de integração de API em `tests/integration/test_chat_api.py`.

### Out-of-Scope
- Protocolo WebSocket (o escopo do projeto padroniza SSE para transmissão unidirecional servidor -> cliente).
- Armazenamento de áudio ou dados multimodais.
