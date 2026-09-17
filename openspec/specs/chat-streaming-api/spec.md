# Spec: Endpoint de Chat com Streaming SSE e Fallback Síncrono

## Requirements

### Requirement: Emissão e Protocolo de Eventos SSE Tipados
O serviço de chat DEVE formatar e emitir eventos Server-Sent Events (SSE) no padrão estrito `event: {event_type}\ndata: {json_str}\n\n`. Os eventos emitidos DEVEM respeitar os esquemas do sistema:
- `event: token` transportando `StreamTokenEvent(token=...)`
- `event: sources` transportando `StreamSourcesEvent(sources=...)`
- `event: done` transportando `StreamDoneEvent(session_id=...)`
- `event: error` transportando `StreamErrorEvent(error=..., code=...)`

A sequência padrão de eventos bem-sucedidos DEVE ser estritamente: um ou mais eventos `token`, seguido exatamente por um evento `sources`, finalizando com um evento `done`.

#### Scenario: Transmissão de eventos SSE em fluxo bem-sucedido
- **GIVEN** uma requisição válida com `stream=True`
- **WHEN** o método `stream_chat` for executado
- **THEN** o gerador assíncrono deve emitir sucessivos eventos `event: token`, seguidos por `event: sources` com a lista de metadados das fontes citadas e, finalmente, `event: done` com o UUID da sessão.

#### Scenario: Falha na geração do modelo de linguagem
- **GIVEN** uma exceção durante a chamada de streaming do modelo de linguagem
- **WHEN** o erro ocorrer no gerador
- **THEN** o gerador deve capturar a exceção e emitir um `event: error` contendo `code="LLM_STREAM_ERROR"` e mensagem explicativa amigável, sem expor o stack trace.

### Requirement: Validação de Guardrails e Resposta de Recusa
Antes de acionar a recuperação RAG ou o modelo de linguagem, o sistema DEVE executar os guardrails de entrada via `validate_input(request.message)`. Caso a entrada seja considerada não permitida (injeção de prompt ou fora de escopo):
- O sistema DEVE salvar a mensagem sanitizada do usuário na sessão conversacional;
- No modo streaming (`stream=True`), o sistema DEVE emitir um evento `token` com o texto de recusa, um evento `sources` com lista vazia e um evento `done` com o `session_id`, encerrando o fluxo sem acionar RAG ou LLM, despachando a persistência da resposta e telemetria em segundo plano;
- No modo síncrono (`stream=False`), o sistema DEVE retornar um `ChatResponse` contendo o texto de recusa e lista de fontes vazia, agendando a persistência e telemetria em segundo plano.

#### Scenario: Entrada violando guardrail de prompt injection
- **GIVEN** uma mensagem de usuário contendo tentativa de injeção de prompt ("Ignore todas as instruções anteriores")
- **WHEN** `stream_chat` ou `process_chat` for acionado
- **THEN** o sistema deve recusar a solicitação, gravar a mensagem do usuário, despachar a persistência da recusa/telemetria em segundo plano e retornar/emitir a mensagem de recusa com fontes vazias.

### Requirement: Resposta de Contingência Normativa (RF-06)
Caso o orquestrador RAG retorne estado de contingência (`rag_result.is_contingency=True`) devido à ausência de fontes com similaridade acima do limiar configurado:
- O sistema DEVE utilizar a mensagem padronizada de contingência (`CONTINGENCY_NO_SOURCES_MESSAGE`);
- No modo streaming (`stream=True`), DEVE emitir evento `token` com o texto de contingência, evento `sources` vazio e evento `done`, despachando a persistência da resposta e telemetria em background;
- No modo síncrono (`stream=False`), DEVE retornar `ChatResponse` com a mensagem de contingência e lista de fontes vazia, agendando a persistência e telemetria em background via `BackgroundTasks`.

#### Scenario: Pergunta sem fontes normativas com similaridade suficiente
- **GIVEN** uma consulta técnica onde o retriever/orquestrador sinaliza contingência
- **WHEN** a consulta for processada
- **THEN** a resposta deve conter o texto padrão de contingência, sem consulta generativa à LLM, com telemetria e mensagem do assistente persistidas assincronamente.

### Requirement: Modo de Fallback Síncrono (stream=False)
O sistema DEVE suportar processamento síncrono completo através do método `process_chat(request: ChatRequest) -> ChatResponse`, retornando o payload consolidado com `session_id`, `response`, `sources` e `created_at` (UTC).

#### Scenario: Requisição com stream desabilitado
- **GIVEN** uma requisição válida com `stream=False`
- **WHEN** `process_chat` for invocado
- **THEN** o retorno deve ser uma instância válida de `ChatResponse` contendo a resposta gerada e os metadados das fontes utilizadas.

### Requirement: Endpoint HTTP POST /api/v1/chat
A API DEVE disponibilizar a rota `POST /api/v1/chat` protegida por `api_key_and_rate_limit` e conectada à sessão transacional de banco de dados (`get_db_session`). O endpoint DEVE validar a sessão informada e responder:
- HTTP 200 com `StreamingResponse(media_type="text/event-stream")` quando `stream=True`, incluindo cabeçalhos `Cache-Control: no-cache` e `Connection: keep-alive`;
- HTTP 200 com payload JSON `ChatResponse` quando `stream=False`;
- HTTP 404 Not Found caso a sessão informada em `request.session_id` não seja localizada;
- HTTP 410 Gone caso a sessão informada esteja expirada por inatividade (> 1 hora conforme RN-05);
- HTTP 401 Unauthorized se a chave de API for ausente ou inválida.

#### Scenario: Requisição SSE bem-sucedida via HTTP
- **GIVEN** uma sessão ativa e chave de API válida
- **WHEN** enviar `POST /api/v1/chat` com `stream=True`
- **THEN** o status HTTP deve ser 200 e o header `Content-Type` deve conter `text/event-stream`.

#### Scenario: Requisição síncrona bem-sucedida via HTTP
- **GIVEN** uma sessão ativa e chave de API válida
- **WHEN** enviar `POST /api/v1/chat` com `stream=False`
- **THEN** o status HTTP deve ser 200 e o corpo da resposta deve ser um JSON válido de `ChatResponse`.

#### Scenario: Sessão inexistente via HTTP
- **GIVEN** um `session_id` que não existe no banco de dados
- **WHEN** enviar `POST /api/v1/chat`
- **THEN** o status retornado deve ser HTTP 404 Not Found.

#### Scenario: Sessão expirada por inatividade via HTTP
- **GIVEN** uma sessão cuja última atualização ocorreu há mais de 1 hora
- **WHEN** enviar `POST /api/v1/chat`
- **THEN** o status retornado deve ser HTTP 410 Gone com mensagem de expiração por inatividade.

### Requirement: Persistência Desacoplada Assíncrona de Mensagens e Telemetria (FEAT-13)
O sistema DEVE persistir a mensagem gerada pelo assistente (`role="assistant"`) e os dados de telemetria analítica (`normative_query_analytics`) de forma desacoplada em segundo plano, utilizando uma sessão assíncrona independente via `get_db_session()`.

No modo streaming SSE (`stream=True`), o despacho da rotina em background DEVE ocorrer imediatamente após a emissão do evento `done`, sem atrasar o recebimento dos tokens nem o término da conexão para o cliente.
No modo síncrono (`stream=False`), a rotina DEVE ser agendada via `FastAPI BackgroundTasks`.

A rotina DEVE cobrir:
1. Respostas RAG bem-sucedidas (com metadados das fontes, documento principal e score máximo de similaridade);
2. Respostas de contingência normativa (com fontes vazias e score nulo);
3. Recusas por guardrails de entrada (com justificativa de recusa e fontes vazias).

Em caso de falha transitória de banco de dados, o worker em segundo plano DEVE realizar 1 retentativa automática após backoff de 500ms, registrando logs estruturados via `structlog` e sem propagar exceções para o consumidor da API.

#### Scenario: Despacho em background pós-evento done em streaming
- **GIVEN** uma consulta técnica processada com `stream=True`
- **WHEN** todos os eventos `token`, `sources` e `done` forem emitidos para o cliente
- **THEN** a persistência da mensagem do assistente e dos registros de telemetria analítica deve ser executada em background em uma sessão de banco independente aberta exclusivamente pelo worker.

#### Scenario: Agendamento via BackgroundTasks em modo síncrono
- **GIVEN** uma requisição POST /api/v1/chat com `stream=False`
- **WHEN** a resposta `ChatResponse` for retornada ao cliente
- **THEN** a persistência da resposta do assistente e do registro de telemetria deve ser realizada assincronamente através de `FastAPI BackgroundTasks`.

#### Scenario: Persistência em contingência e recusa por guardrails
- **GIVEN** uma consulta que dispara contingência normativa ou recusa por guardrail
- **WHEN** o fluxo for finalizado
- **THEN** a telemetria deve ser persistida com a respectiva latência em ms, registrando campos de documento e similaridade como nulos.

#### Scenario: Resiliência e retentativa em falha de persistência
- **GIVEN** uma falha temporária de conexão com o banco de dados durante a execução do worker
- **WHEN** a persistência falhar na primeira tentativa
- **THEN** o worker deve aguardar 500ms e realizar uma segunda tentativa; persistindo com sucesso ou registrando erro no structlog sem quebrar a API.
