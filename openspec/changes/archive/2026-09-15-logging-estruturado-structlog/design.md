# Design: Logging Estruturado, Correlação Assíncrona e Redaction

## Context & Problem Statement
A arquitetura do Lumi API processa chamadas de engenharia de alta complexidade com múltiplos pontos assíncronos: FastAPI, SQLAlchemy com pool de conexões asyncpg, e integrações externas com provedores LLM. Quando ocorrem anomalias ou falhas de conectividade, a correlação entre a requisição externa do cliente, as queries executadas e as mensagens do framework é essencial para o diagnóstico sem expor dados confidenciais (como API Keys).

## Architecture Overview

```
                        [ Cliente HTTP ]
                               |
                   X-Request-ID (ou gera UUIDv4)
                               v
               +-------------------------------+
               |    CorrelationIdMiddleware    |
               | - bind_contextvars(request_id)|
               | - log("request_started")      |
               +-------------------------------+
                               |
                               v
                       [ FastAPI Routes ]
                               |
               +-------------------------------+
               |       structlog Pipeline      |
               | - merge_contextvars           |
               | - add_log_level               |
               | - TimeStamper(iso)            |
               | - redact_sensitive_data       |
               | - JSONRenderer/ConsoleRenderer|
               +-------------------------------+
                               |
                               v
               [ Output: stdout / contêiner ]
```

## Detailed Component Design

### 1. `src/lumi/core/logging.py`
- `setup_logging(environment: str | None = None, log_level: str | None = None) -> None`:
  - Carrega configurações de `get_settings()` como fallback padrão.
  - Define a lista de processadores compartilhados (`shared_processors`):
    - `structlog.contextvars.merge_contextvars`
    - `structlog.processors.add_log_level`
    - `structlog.processors.TimeStamper(fmt="iso")`
    - `structlog.processors.StackInfoRenderer()`
    - `structlog.processors.format_exc_info`
    - `redact_sensitive_data`
  - Seleciona o formatador final:
    - Se `environment in ("production", "staging")`: `structlog.processors.JSONRenderer()`
    - Caso contrário: `structlog.dev.ConsoleRenderer(colors=True)`
  - Configura o `structlog` via `structlog.configure()` com `wrap_for_formatter`.
  - Configura o logging da standard library com `ProcessorFormatter`, associando ao `root_logger` e explicitamente aos loggers:
    - `uvicorn`
    - `uvicorn.access`
    - `uvicorn.error`
    - `sqlalchemy.engine`

### 2. Processador Defensivo `redact_sensitive_data`
- Chaves protegidas: `'api_key', 'x-api-key', 'authorization', 'password', 'token', 'secret', 'access_token', 'cookie'`.
- Normalização de chave: `k.lower()` com suporte a variações de hífen e sublinhado.
- Varredura recursiva de dicionários, listas e tuplas, substituindo valores por `"[REDACTED]"`.

### 3. `src/lumi/api/middleware.py`
- `CorrelationIdMiddleware(BaseHTTPMiddleware)`:
  - Intercepta todas as requisições HTTP.
  - Extrai `request.headers.get("X-Request-ID")` ou gera `str(uuid.uuid4())`.
  - Vincula `request_id` às `contextvars` do structlog.
  - Registra o evento `request_started` com método e caminho.
  - Executa o handler e captura o tempo de latência (`duration_ms = (t1 - t0) * 1000`).
  - Injeta o `X-Request-ID` no cabeçalho da resposta.
  - Registra o evento `request_finished` com método, caminho, código de status e duração em ms.
  - Em bloco `finally`, invoca `structlog.contextvars.clear_contextvars()`.

### 4. `src/lumi/main.py`
- Chama `setup_logging()` antes de instanciar `app = FastAPI(...)`.
- Adiciona `app.add_middleware(CorrelationIdMiddleware)`.
