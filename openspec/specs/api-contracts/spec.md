# Spec: Contratos de API (Chat, Sessão e Streaming SSE)

## Requirements

### Requirement: Validação de Metadados de Fontes Normativas (SourceMetadata)
O sistema DEVE validar estruturadamente cada fonte normativa anexada a uma resposta de assistência técnica, contendo código do documento, revisão, seção, número da página (`>= 1`), pontuação de relevância (entre `0.0` e `1.0`) e trecho citado (`snippet`).

#### Scenario: Instanciação válida de fonte normativa
- **GIVEN** dados de uma citação com documento "DIS-NOR-030", revisão "REV07", seção "Item 5.3", página 28, score 0.89 e trecho de texto
- **WHEN** o modelo `SourceMetadata` for instanciado
- **THEN** os atributos devem ser validados e preservados com seus tipos corretos.

#### Scenario: Rejeição de número de página menor que 1
- **GIVEN** uma tentativa de instanciar `SourceMetadata` com `page = 0` ou `page = -5`
- **WHEN** a validação do Pydantic for executada
- **THEN** um `ValidationError` deve ser gerado indicando restrição de valor maior ou igual a 1.

#### Scenario: Rejeição de score de relevância fora do intervalo [0.0, 1.0]
- **GIVEN** uma tentativa de instanciar `SourceMetadata` com `relevance_score = 1.5` ou `-0.1`
- **WHEN** a validação do Pydantic for executada
- **THEN** um `ValidationError` deve ser gerado indicando violação dos limites permitidos.

---

### Requirement: Contratos de Mensagem e Resposta do Chat (ChatRequest e ChatResponse)
O sistema DEVE fornecer modelos Pydantic estritos para requisição e resposta do endpoint conversacional `/api/v1/chat`.

#### Scenario: Requisição de chat válida com stream padrão
- **GIVEN** um `session_id` UUID válido e uma mensagem de texto não-vazia
- **WHEN** o modelo `ChatRequest` for criado sem especificar o campo `stream`
- **THEN** o campo `stream` deve assumir o valor default `True`.

#### Scenario: Rejeição de mensagem em branco ou vazia
- **GIVEN** um payload com `message` vazia (`""`) ou contendo apenas espaços em branco (`"   "`)
- **WHEN** o modelo `ChatRequest` for validado
- **THEN** um `ValidationError` deve ser disparado rejeitando o payload.

#### Scenario: Rejeição de session_id com formato UUID inválido
- **GIVEN** uma string que não represente um UUID válido (ex.: `"invalido-123"`)
- **WHEN** o modelo `ChatRequest` for validado
- **THEN** a conversão para `UUID` deve falhar emitindo um `ValidationError`.

#### Scenario: Resposta síncrona de chat com fontes normativas
- **GIVEN** um `session_id`, texto de resposta e uma lista de objetos `SourceMetadata`
- **WHEN** o modelo `ChatResponse` for instanciado
- **THEN** o campo `created_at` deve ser preenchido com timestamp UTC válido e as fontes estruturadas devem ser acessíveis.

---

### Requirement: Contratos de Eventos de Streaming SSE
O sistema DEVE definir contratos para todos os eventos transmitidos via Server-Sent Events durante a resposta gerada por IA.

#### Scenario: Evento de transmissão de token (StreamTokenEvent)
- **GIVEN** um fragmento textual de resposta emitido pelo modelo generativo
- **WHEN** o modelo `StreamTokenEvent` for instanciado com o campo `token`
- **THEN** o token deve ser preservado exatamente como gerado.

#### Scenario: Evento de catálogo de fontes (StreamSourcesEvent)
- **GIVEN** uma lista de instâncias ou dicionários de `SourceMetadata`
- **WHEN** o modelo `StreamSourcesEvent` for instanciado
- **THEN** o campo `sources` deve validar e conter a lista de fontes normativas.

#### Scenario: Evento de encerramento do stream (StreamDoneEvent)
- **GIVEN** o identificador de sessão UUID da conversa
- **WHEN** o modelo `StreamDoneEvent` for instanciado
- **THEN** o `session_id` deve ser validado como UUID.

#### Scenario: Evento de erro durante streaming (StreamErrorEvent)
- **GIVEN** uma mensagem de erro e um código explicativo (ex.: `"LLM_STREAM_ERROR"`)
- **WHEN** o modelo `StreamErrorEvent` for instanciado
- **THEN** os campos `error` e `code` devem ser validados como strings obrigatórias.

---

### Requirement: Contratos de Gestão de Sessão e Histórico
O sistema DEVE definir modelos para criação e detalhamento de sessões e mensagens arquivadas.

#### Scenario: Criação de sessão com identificador UUID
- **GIVEN** um UUID de sessão e timestamp de criação
- **WHEN** o modelo `SessionCreateResponse` for instanciado
- **THEN** o identificador deve ser acessível tanto por `id` quanto por `session_id`.

#### Scenario: Registro de mensagem com papéis estritos
- **GIVEN** mensagens com papéis `"user"`, `"assistant"` ou `"system"`
- **WHEN** o modelo `ChatMessageResponse` for instanciado
- **THEN** os atributos de papel, conteúdo, fontes e timestamp devem ser validados com sucesso.

#### Scenario: Rejeição de papel inválido no histórico
- **GIVEN** um papel fora dos literais permitidos (ex.: `"admin"`, `"bot"`, `"guest"`)
- **WHEN** o modelo `ChatMessageResponse` for instanciado
- **THEN** um `ValidationError` deve ser disparado recusando o registro.

#### Scenario: Detalhamento de sessão com histórico completo
- **GIVEN** um identificador de sessão e uma lista de mensagens `ChatMessageResponse`
- **WHEN** o modelo `SessionDetailResponse` for instanciado
- **THEN** a sessão deve expor metadados temporais (`created_at`, `updated_at`) e a lista íntegra de mensagens.
