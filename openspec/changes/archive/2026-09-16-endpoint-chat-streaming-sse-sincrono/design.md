# Design: Endpoint de Chat com Streaming SSE e Fallback Síncrono

## Arquitetura e Decisões Técnicas

### 1. Camada de Serviço (`ChatService`)
A classe `ChatService` em `src/lumi/services/chat_service.py` centraliza a lógica de negócios da conversação:
- Injeção flexível de dependências com inicialização tardia (lazy properties):
  - `session: AsyncSession`
  - `llm: BaseChatModel | None` (se `None`, obtido via `get_llm(temperature=0.0, settings=self.settings)`)
  - `rag_orchestrator: RagContextOrchestrator | None` (se `None`, composto por `NormativeRetriever`, `QueryRewriter` e `NormativeReranker`)
  - `session_service: SessionService | None` (se `None`, instanciado com `session` e `settings`)
  - `settings: Settings | None`

### 2. Formatação do Protocolo SSE
Os eventos Server-Sent Events seguem estritamente a especificação W3C SSE:
```
event: <tipo_evento>\n
data: <payload_json_compacto>\n
\n
```
Tipos de eventos emitidos:
1. `token`: fragmentos incrementais gerados pelo modelo (`StreamTokenEvent`).
2. `sources`: lista consolidada de fontes normativas citadas (`StreamSourcesEvent`).
3. `done`: finalização da sessão com sucesso (`StreamDoneEvent`).
4. `error`: notificação amigável de falha estruturada (`StreamErrorEvent`).

### 3. Fluxo de Execução de `stream_chat`
1. **Validação da Sessão**: invoca `await self.session_service.get_session_or_raise(request.session_id, check_ttl=True)`. Erros como `SessionNotFoundError` e `SessionExpiredError` são propagados.
2. **Avaliação de Guardrails**: executa `validate_input(request.message)`.
   - Se `not guard_result.is_allowed`:
     - Grava pergunta sanitizada e resposta do assistente (com motivo da recusa) no banco via `session_service.add_message`.
     - Emite `event: token` com o texto da recusa.
     - Emite `event: sources` com lista vazia `sources=[]`.
     - Emite `event: done` com `request.session_id`.
     - Encerra a execução (`return`).
3. **Histórico Multi-Turn e Persistência da Pergunta**:
   - Recupera histórico recente anterior à pergunta atual via `session_service.get_langchain_messages(..., limit=chat_history_limit)`.
   - Persiste a pergunta sanitizada do usuário via `session_service.add_message(request.session_id, role="user", content=guard_result.sanitized_text)`.
4. **Contextualização RAG**:
   - Executa `rag_result = await self.rag_orchestrator.get_context(guard_result.sanitized_text, chat_history=history_before_query)`.
5. **Avaliação de Contingência Normativa**:
   - Se `rag_result.is_contingency`:
     - Determina texto: `rag_result.contingency_message or CONTINGENCY_NO_SOURCES_MESSAGE`.
     - Grava resposta do assistente no banco.
     - Emite `token` com texto de contingência, `sources` com `[]` e `done`.
     - Encerra a execução (`return`).
6. **Geração via LLM Streaming**:
   - Monta prompt com `get_rag_prompt_template().format_messages(...)` injetando contexto normativo, histórico anterior e pergunta sanitizada.
   - Itera assincronamente por `chunk` em `self.llm.astream(prompt_messages)`, emitindo eventos `token` e acumulando o texto gerado.
   - Emite evento `sources` com `rag_result.sources`.
   - Emite evento `done` com `request.session_id`.
   - Persiste a mensagem completa gerada pelo assistente com a lista de metadados das fontes citadas via `session_service.add_message`.
7. **Tratamento de Exceções**:
   - Bloco defensivo `try/except Exception` durante a geração capturando falhas da LLM/rede e emitindo `event: error` com código `LLM_STREAM_ERROR` e mensagem amigável sem expor dados sensíveis de infraestrutura.

### 4. Fluxo Síncrono `process_chat`
- Executa a mesma orquestração lógica de validação, guardrails, histórico, RAG e contingência.
- Invoca a LLM de forma síncrona/awaitable via `await self.llm.ainvoke(...)`.
- Retorna diretamente uma instância de `ChatResponse(session_id=..., response=..., sources=..., created_at=...)`.

### 5. Camada HTTP e FastAPI (`src/lumi/api/v1/chat.py`)
- Rota: `POST /api/v1/chat` (com alias `/`).
- Autenticação e Rate Limit: `_auth: Annotated[str, Depends(api_key_and_rate_limit)]`.
- Sessão transacional: `db: Annotated[AsyncSession, Depends(get_db_session)]`.
- Validação antecipada da sessão para garantir códigos HTTP 404/410 antes do envio de cabeçalhos de resposta HTTP:
  - Se `SessionNotFoundError` -> HTTP 404.
  - Se `SessionExpiredError` -> HTTP 410.
- Despacho:
  - Se `request.stream` (`True` por padrão):
    - Retorna `StreamingResponse(chat_service.stream_chat(request), media_type="text/event-stream")` com cabeçalhos `Cache-Control: no-cache` e `Connection: keep-alive`.
  - Se não `request.stream`:
    - Retorna `await chat_service.process_chat(request)` (HTTP 200 com payload `ChatResponse`).
