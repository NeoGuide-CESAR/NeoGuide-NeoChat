# Design: Schemas Pydantic para Validação de Contratos da API (Chat e Sessão)

## Technical Decisions

### 1. Pydantic v2 Core e Validação Estrita
- Utilização de `pydantic.BaseModel` e anotações nativas do Python 3.12+ (`UUID`, `datetime`, `Literal`, `list`).
- Validação estrita de restrições numéricas com `Field(ge=..., le=...)` para `page` e `relevance_score`.
- Validação personalizada via `@field_validator` em `ChatRequest.message` para prevenir strings vazias ou compostas unicamente por espaços em branco, higienizando o texto de entrada.

### 2. Separação de Módulos e Responsabilidades
A pasta `src/lumi/schemas/` será dividida em:
- `src/lumi/schemas/chat.py`: Contratos de interação direta com o assistente normativo, incluindo metadados de normas (`SourceMetadata`), DTOs de pergunta/resposta (`ChatRequest`, `ChatResponse`) e eventos de streaming SSE (`StreamTokenEvent`, `StreamSourcesEvent`, `StreamDoneEvent`, `StreamErrorEvent`).
- `src/lumi/schemas/session.py`: Modelos focados no ciclo de vida de conversas e persistência multi-turn (`SessionCreateResponse`, `ChatMessageResponse`, `SessionDetailResponse`).
- `src/lumi/schemas/__init__.py`: Ponto único de exportação dos DTOs públicos, permitindo importações limpas como `from lumi.schemas import ChatRequest, SourceMetadata`.

### 3. Interoperabilidade de Identificadores (id vs. session_id)
- Para manter conformidade com a convenção RESTful padrão (`id`) e com as interfaces de cliente que referenciam explicitamente `session_id`, `SessionCreateResponse` e `SessionDetailResponse` adotam `AliasChoices("id", "session_id")` ou propriedade computada `session_id`, garantindo que tanto `obj.id` quanto `obj.session_id` funcionem indistintamente.

### 4. Protocolo Server-Sent Events (SSE)
- Conforme documentado em `docs/04-FLUXOS.md` e `docs/05-ARQUITETURA.md`, as transmissões parciais enviam eventos estruturados:
  - `StreamTokenEvent`: carrega cada token gerado (`{"token": "..."}`).
  - `StreamSourcesEvent`: transporta a lista de citações normativas validadas com `SourceMetadata`.
  - `StreamDoneEvent`: sinaliza o encerramento do stream com confirmação do `session_id`.
  - `StreamErrorEvent`: encapsula falhas parciais do LLM com mensagem amigável e código de erro.

### 5. Resiliência Temporal e Defaults
- Campos datetime utilizam `datetime.now(timezone.utc)` para garantir consistência de fuso horário internacional (ISO 8601 UTC).
- Listas de metadados (`sources`, `messages`) utilizam `Field(default_factory=list)` para evitar efeitos colaterais com objetos mutáveis.
