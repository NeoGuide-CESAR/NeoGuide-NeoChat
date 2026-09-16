# Proposal: Gerenciamento de Ciclo de Vida de Sessões e Histórico Multi-turn com TTL

## Context
A API do Lumi (NeoGuide) atua como um assistente técnico inteligente voltado para normas e procedimentos de infraestrutura de telecomunicações. As interações do usuário com o assistente necessitam de persistência conversacional contextual (multi-turn), permitindo que perguntas subsequentes utilizem mensagens anteriores como histórico contextual na montagem do prompt RAG. Adicionalmente, para segurança e conservação de recursos de armazenamento, sessões inativas devem expirar após uma janela de inatividade predeterminada (TTL de 1 hora conforme RN-05).

## Motivation & Value
1. **Persistência Conversacional Transacional**: Permitir a criação de sessões dedicadas (`ChatSession`) e registro cronológico ordenado de interações (`ChatMessage`) com suporte a metadados normativos de citação.
2. **Contexto Multi-turn para LLM**: Fornecer recuperação otimizada das mensagens mais recentes da sessão, convertendo-as diretamente para abstrações padrão do LangChain (`HumanMessage`, `AIMessage`, `SystemMessage`) prontas para injeção no prompt de orquestração.
3. **Controle Estrito de TTL (RN-05)**: Bloquear sessões inativas por mais de 1 hora levantando exceção de domínio `SessionExpiredError` e respondendo HTTP 410 Gone na API REST.
4. **Endpoints REST Seguros**: Disponibilizar rotas públicas padronizadas `POST /api/v1/sessions` e `GET /api/v1/sessions/{session_id}` protegidas por chave de API e limitação de taxa (`api_key_and_rate_limit`).

## Scope

### In-Scope
- Atualização das configurações em `src/lumi/core/config.py`:
  - `session_ttl_hours: int = 1` (conforme RN-05).
  - `chat_history_limit: int = 10` (janela padrão multi-turn).
- Criação do serviço `SessionService` em `src/lumi/services/session_service.py` com exceções `SessionError`, `SessionNotFoundError` e `SessionExpiredError`.
- Métodos do serviço:
  - `create_session(session_id: UUID | None = None) -> ChatSession`
  - `get_session(session_id: UUID, check_ttl: bool = True) -> ChatSession | None`
  - `get_session_or_raise(session_id: UUID, check_ttl: bool = True) -> ChatSession`
  - `add_message(session_id: UUID, role: str, content: str, sources: list[dict[str, Any]] | None = None) -> ChatMessage`
  - `get_history(session_id: UUID, limit: int | None = None) -> list[ChatMessage]` (ordem ASC)
  - `get_langchain_messages(session_id: UUID, limit: int | None = None) -> list[BaseMessage]`
- Exportação em `src/lumi/services/__init__.py`.
- Endpoints REST em `src/lumi/api/v1/sessions.py` e inclusão no roteador `src/lumi/api/v1/router.py`:
  - `POST /api/v1/sessions` (201 Created)
  - `GET /api/v1/sessions/{session_id}` (200 OK, 404 Not Found, 410 Gone)
- Testes unitários em `tests/unit/test_session_service.py` e de integração em `tests/integration/test_sessions_api.py`.

### Out-of-Scope
- Armazenamento de sessões em cache distribuído Redis (mantido no PostgreSQL via SQLAlchemy).
- Deleção manual / arquivamento de sessões por endpoint REST (coberto em tarefas futuras de auditoria/cleanup).
