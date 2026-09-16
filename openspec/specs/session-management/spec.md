# Spec: Gerenciamento de Sessões, Histórico Multi-turn e TTL

## Requirements

### Requirement: Criação e Ciclo de Vida de Sessões de Chat
O sistema DEVE permitir a criação de novas sessões de conversação (`ChatSession`) gerando identificadores UUID únicos caso nenhum seja fornecido, ou respeitando um UUID pré-gerado, persistindo os timestamps de criação (`created_at`) e atualização (`updated_at`) em UTC.

#### Scenario: Criação de sessão sem identificador prévio
- **GIVEN** uma requisição de criação de sessão
- **WHEN** `create_session()` for invocado sem fornecer `session_id`
- **THEN** uma nova `ChatSession` deve ser criada e persistida com um UUID v4 único e timestamps UTC válidos.

#### Scenario: Criação de sessão com identificador explícito
- **GIVEN** um `session_id` UUID válido fornecido pelo chamador
- **WHEN** `create_session(session_id)` for invocado
- **THEN** a `ChatSession` resultante deve ter o ID correspondente ao fornecido.

### Requirement: Recuperação de Sessão e Expiração por Inatividade (TTL de 1h)
O sistema DEVE recuperar sessões persistidas a partir do identificador `session_id`. Quando `check_ttl=True`, o sistema DEVE verificar a diferença de tempo entre o instante atual (`datetime.now(UTC)`) e o timestamp `session.updated_at`. Caso a diferença ultrapasse `settings.session_ttl_hours` (padrão 1 hora conforme RN-05), a sessão DEVE ser considerada expirada e o sistema DEVE levantar `SessionExpiredError`. Caso a sessão não exista no banco de dados, o método `get_session_or_raise` DEVE levantar `SessionNotFoundError`.

#### Scenario: Recuperação de sessão ativa dentro do prazo de TTL
- **GIVEN** uma sessão com última interação (`updated_at`) ocorrida há menos de 1 hora
- **WHEN** `get_session(session_id, check_ttl=True)` for invocado
- **THEN** o objeto `ChatSession` deve ser retornado com sucesso.

#### Scenario: Sessão expirada por inatividade superior ao TTL
- **GIVEN** uma sessão com última interação (`updated_at`) ocorrida há mais de 1 hora
- **WHEN** `get_session(session_id, check_ttl=True)` for invocado
- **THEN** deve ser levantada a exceção `SessionExpiredError`.

#### Scenario: Busca por sessão inexistente
- **GIVEN** um UUID de sessão inexistente no banco de dados
- **WHEN** `get_session_or_raise(session_id)` for invocado
- **THEN** deve ser levantada a exceção `SessionNotFoundError`.

### Requirement: Registro de Mensagens e Renovação do TTL
O sistema DEVE permitir a adição de mensagens (`ChatMessage`) vinculadas a uma sessão ativa, registrando o papel (`role`), conteúdo textual e metadados de fontes normativas (`sources`). A adição de qualquer mensagem DEVE atualizar imediatamente o campo `session.updated_at` com o timestamp UTC atual, renovando a janela de TTL da sessão.

#### Scenario: Inclusão de mensagem em sessão ativa
- **GIVEN** uma sessão ativa válida
- **WHEN** `add_message(session_id, role="user", content="Pergunta técnica")` for invocado
- **THEN** uma nova `ChatMessage` deve ser persistida e o `updated_at` da sessão deve ser atualizado para o horário corrente UTC.

#### Scenario: Tentativa de inclusão de mensagem em sessão expirada
- **GIVEN** uma sessão inativa há mais de 1 hora
- **WHEN** `add_message(session_id, role="user", content="Pergunta")` for invocado
- **THEN** deve ser levantada `SessionExpiredError` e nenhuma mensagem deve ser gravada.

### Requirement: Recuperação de Histórico Ordenado e Conversão LangChain
O sistema DEVE permitir a recuperação do histórico de mensagens em ordem cronológica estritamente crescente (`ChatMessage.created_at.asc()`), suportando limitação das N mensagens mais recentes para a janela de contexto. O sistema DEVE também fornecer o método `get_langchain_messages()` convertendo as mensagens registradas para objetos de mensagem nativos do LangChain (`HumanMessage` para role "user", `AIMessage` para role "assistant" e `SystemMessage` para role "system").

#### Scenario: Recuperação de histórico com limite de janela
- **GIVEN** uma sessão contendo 15 mensagens registradas
- **WHEN** `get_history(session_id, limit=10)` for invocado
- **THEN** as 10 mensagens mais recentes devem ser retornadas em ordem cronológica ascendente (mais antiga para a mais recente dentro da janela).

#### Scenario: Conversão para mensagens LangChain
- **GIVEN** um histórico composto por mensagens com papéis "user", "assistant" e "system"
- **WHEN** `get_langchain_messages(session_id)` for invocado
- **THEN** deve retornar uma lista de `BaseMessage` contendo instâncias correspondentes de `HumanMessage`, `AIMessage` e `SystemMessage` preservando a ordem cronológica e o conteúdo textual.

### Requirement: Endpoints REST de Sessões v1
A API DEVE expor as rotas `POST /api/v1/sessions` e `GET /api/v1/sessions/{session_id}` protegidas por autenticação via `X-API-Key` e rate limiting (`api_key_and_rate_limit`). `POST /api/v1/sessions` deve retornar HTTP 201 Created com o payload `SessionCreateResponse`. `GET /api/v1/sessions/{session_id}` deve retornar HTTP 200 OK com o payload `SessionDetailResponse` incluindo o histórico ordenado de mensagens. Caso a sessão não seja encontrada, deve retornar HTTP 404 Not Found; se estiver expirada por TTL, deve retornar HTTP 410 Gone com a mensagem `"Sessão expirada por inatividade."`.

#### Scenario: Criação de sessão via API REST
- **GIVEN** cliente autenticado com cabeçalho `X-API-Key` válido
- **WHEN** enviar requisição `POST /api/v1/sessions`
- **THEN** deve retornar status HTTP 201 Created com payload compatível com `SessionCreateResponse`.

#### Scenario: Detalhamento de sessão existente com histórico
- **GIVEN** uma sessão ativa contendo mensagens persistidas
- **WHEN** enviar requisição `GET /api/v1/sessions/{session_id}`
- **THEN** deve retornar status HTTP 200 OK com payload `SessionDetailResponse` contendo a lista cronológica de mensagens.

#### Scenario: Detalhamento de sessão expirada via API REST
- **GIVEN** uma sessão inativa há mais de 1 hora
- **WHEN** enviar requisição `GET /api/v1/sessions/{session_id}`
- **THEN** deve retornar status HTTP 410 Gone com `{"detail": "Sessão expirada por inatividade."}`.

#### Scenario: Requisição sem autenticação
- **GIVEN** qualquer endpoint de sessão
- **WHEN** a requisição for enviada sem `X-API-Key` ou com chave inválida
- **THEN** a API deve retornar status HTTP 401 Unauthorized.
