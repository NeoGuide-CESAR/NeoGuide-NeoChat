# Design: Gerenciamento de Sessões, Histórico Multi-turn e TTL

## Arquitetura e Decisões Técnicas

### 1. Camada de Domínio e Exceções
Definição de uma hierarquia clara de exceções em `src/lumi/services/session_service.py`:
- `SessionError(Exception)`: Exceção base para todas as falhas de sessão.
- `SessionNotFoundError(SessionError)`: Lançada quando o identificador de sessão não existe.
- `SessionExpiredError(SessionError)`: Lançada quando a sessão ultrapassou o tempo limite de inatividade (`session_ttl_hours`).

### 2. Classe `SessionService`
A classe atua como a porta de entrada lógica e transacional para manipulação de sessões e mensagens no SQLAlchemy:
```python
class SessionService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
```

#### Métodos:
- `create_session(session_id: UUID | None = None) -> ChatSession`: Instancia `ChatSession` com UUID (gerado ou informado), adiciona à `self.session` e realiza `await self.session.flush()`.
- `get_session(session_id: UUID, check_ttl: bool = True) -> ChatSession | None`: Executa query `select(ChatSession).where(ChatSession.id == session_id)`. Se encontrada e `check_ttl=True`, compara `(datetime.now(UTC) - session.updated_at).total_seconds()` contra `settings.session_ttl_hours * 3600`. Se expirada, levanta `SessionExpiredError`.
- `get_session_or_raise(session_id: UUID, check_ttl: bool = True) -> ChatSession`: Wrapper que levanta `SessionNotFoundError` se o retorno de `get_session` for `None`.
- `add_message(session_id: UUID, role: str, content: str, sources: list[dict[str, Any]] | None = None) -> ChatMessage`: Valida existência e TTL chamando `get_session_or_raise`. Atualiza `session.updated_at = datetime.now(UTC)`. Cria `ChatMessage`, adiciona e realiza `flush()`.
- `get_history(session_id: UUID, limit: int | None = None) -> list[ChatMessage]`: Valida a sessão. Se `limit` for informado, seleciona os `limit` registros mais recentes (`order_by(ChatMessage.created_at.desc())`), invertendo a lista para entrega em ordem estritamente cronológica (`ASC`). Se `limit` for `None`, busca diretamente em ordem ascendente.
- `get_langchain_messages(session_id: UUID, limit: int | None = None) -> list[BaseMessage]`: Itera sobre o histórico obtido por `get_history` e mapeia para `HumanMessage(content=...)` se role "user", `AIMessage(content=...)` se role "assistant", ou `SystemMessage(content=...)` se role "system".

### 3. Configurações de Sistema (`Settings`)
Em `src/lumi/core/config.py`:
- `session_ttl_hours: int = Field(default=1, description="TTL em horas para expiração de sessões")` (alinhado a RN-05).
- `chat_history_limit: int = Field(default=10, description="Limite padrão de mensagens recentes na janela multi-turn")`.

### 4. Camada de API REST (`src/lumi/api/v1/sessions.py`)
Roteador FastAPI montado em `src/lumi/api/v1/router.py` sob prefixo `/sessions` com tag `"Sessões v1"`:
- `POST /api/v1/sessions`:
  - Dependências: `api_key_and_rate_limit`, `get_db_session` (ou gerador de sessão injetável).
  - Status HTTP: `201 Created`.
  - Schema de resposta: `SessionCreateResponse`.
- `GET /api/v1/sessions/{session_id}`:
  - Dependências: `api_key_and_rate_limit`, `get_db_session`.
  - Status HTTP: `200 OK`.
  - Schema de resposta: `SessionDetailResponse` com array de `ChatMessageResponse`.
  - Mapeamento de erros:
    - `SessionNotFoundError` -> `HTTPException(status_code=404, detail="Sessão {session_id} não encontrada.")`
    - `SessionExpiredError` -> `HTTPException(status_code=410, detail="Sessão expirada por inatividade.")`
