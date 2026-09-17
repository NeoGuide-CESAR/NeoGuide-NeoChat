# Spec: Endpoint de Chat com Streaming SSE e Fallback Síncrono

## Requirements

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
