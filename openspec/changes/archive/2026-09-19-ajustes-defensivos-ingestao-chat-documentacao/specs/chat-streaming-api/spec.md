# Delta Spec: Endpoint de Chat com Streaming SSE e Fallback Síncrono

## ADDED Requirements

### Requirement: Persistência Antecipada da Mensagem do Usuário
O `ChatService` DEVE efetivar a persistência (`commit()`) da mensagem sanitizada do usuário no banco relacional antes de delegar a requisição ao orquestrador RAG e ao modelo de linguagem, tanto no fluxo de streaming quanto no síncrono.

#### Scenario: Falha posterior na rede ou no modelo de linguagem
- **GIVEN** uma mensagem recebida e validada pelos guardrails
- **WHEN** a mensagem for salva no repositório de sessão
- **THEN** a transação deve ser confirmada imediatamente via `await session.commit()`, assegurando que o registro da pergunta persista mesmo se a consulta ao LLM falhar.

### Requirement: Tratamento Resiliente de Sobrecarga de Modelo no Modo Síncrono (HTTP 503)
Na invocação síncrona `process_chat`, caso a chamada ao modelo gerador (`llm.ainvoke`) lance qualquer exceção (como timeout, alta demanda ou falha de conectividade do provedor), o serviço DEVE registrar log estruturado de erro com os identificadores da sessão e propagar `HTTPException` com status 503 (Service Unavailable) contendo mensagem clara orientando nova tentativa em alguns segundos.

#### Scenario: Provedor indisponível na chamada síncrona
- **GIVEN** uma requisição de chat com `stream=False`
- **WHEN** a chamada ao modelo de linguagem falhar
- **THEN** o serviço deve registrar log estruturado `chat_service_llm_invoke_error` e lançar `HTTPException` com código 503 e mensagem explicativa ao cliente.
