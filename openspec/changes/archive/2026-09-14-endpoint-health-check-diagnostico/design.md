# Design: Endpoint de Health Check e Diagnóstico de Conectividade

## Arquitetura Geral

O design da solução divide as responsabilidades em camadas bem delimitadas:

```
[ Cliente / Monitoramento ]
         │
         ├── GET /health (sem autenticação) ────────────> [ Sonda de Liveness (Processo HTTP Ativo) ]
         │
         └── GET /api/v1/health (com X-API-Key)
                     │
            [ api_key_and_rate_limit ]
                     │
            [ api/v1/health:get_health_check ]
                     │
            [ db/session:get_db_session ]
                     │
            ┌────────┴───────────────────────────┐
            │ 1. SELECT 1 (medição latência)     │
            │ 2. SELECT extversion FROM ...      │
            └────────┬───────────────────────────┘
                     │
           [ schemas/health:HealthCheckResponse ]
```

## Componentes

### 1. Schemas de Dados (`src/lumi/schemas/health.py`)
Modelagem baseada em Pydantic v2 garantindo serialização consistente e tipos explícitos:
- `DatabaseHealthInfo`:
  - `status`: Literal `"connected"`, `"disconnected"`, `"error"`
  - `latency_ms`: `float | None` (arredondado em 2 casas decimais)
  - `pgvector_installed`: `bool` (True se a extensão existir no Postgres)
  - `pgvector_version`: `str | None` (ex: "0.7.0")
  - `error`: `str | None` (mensagem amigável sanitizada em caso de erro)
- `HealthCheckResponse`:
  - `status`: Literal `"healthy"`, `"unhealthy"`, `"degraded"`
  - `version`: `str` (versão da aplicação Lumi)
  - `environment`: `str` (ambiente de execução: "development", "production", etc.)
  - `timestamp`: `datetime` (UTC com timezone)
  - `database`: `DatabaseHealthInfo`

### 2. Infraestrutura de Banco de Dados (`src/lumi/db/session.py`)
- Configuração do SQLAlchemy AsyncEngine com driver `postgresql+asyncpg`.
- Pooling otimizado utilizando `settings.db_pool_size`, `settings.db_max_overflow` e `settings.db_pool_timeout`.
- Função/context manager `get_db_session()`:
  - Permite uso com `async with get_db_session() as session:`.
  - Suporta override de dependência no FastAPI para injeção de mocks em testes unitários.
  - Função `get_async_session()` compatível com `Depends(get_async_session)` para facilidade de testes e desacoplamento.

### 3. Roteamento Modular v1 (`src/lumi/api/v1/`)
- `src/lumi/api/v1/__init__.py`: Exporta roteadores principais.
- `src/lumi/api/v1/health.py`:
  - Define `router = APIRouter()`.
  - Endpoint `GET /health` (ou base) protegido por `_ = Depends(api_key_and_rate_limit)`.
  - Executa:
    1. Início de timer (`perf_counter`).
    2. Execução de `SELECT 1` via `session.execute(text("SELECT 1"))`.
    3. Fim de timer e cálculo de `latency_ms`.
    4. Consulta da extensão: `SELECT extversion FROM pg_extension WHERE extname = 'vector'`.
    5. Se pgvector encontrado: status `"healthy"`, `pgvector_installed=True`, `pgvector_version=...`.
    6. Se pgvector não instalado: status `"degraded"`, `pgvector_installed=False`, `pgvector_version=None`.
  - Em caso de falha de conexão ou erro do banco:
    - Captura defensiva de `Exception`.
    - Resposta HTTP 503 com status geral `"unhealthy"`, `database.status="error"`, mensagem sanitizada (sem senhas ou parâmetros sensíveis da URL).
- `src/lumi/api/v1/router.py`:
  - Define `api_v1_router = APIRouter()`.
  - Inclui `health.router` sob o prefixo `/health` (ou mapeado para que a URL final seja `/api/v1/health`).
- `src/lumi/main.py`:
  - Inclui `api_v1_router` com prefixo `/api/v1`.
  - Mantém `/health` público na raiz.

### 4. Tolerância a Falhas e Segurança
- O endpoint `/api/v1/health` nunca retorna stack trace ou string de conexão bruta contendo senhas.
- Em caso de exceção de banco de dados, o erro retornado no payload é sumarizado de forma segura (ex: `"Database connection failed: <sanitized_reason>"`).
- O código de status HTTP reflete a integridade:
  - 200: Healthy (ou Degraded quando operacional com ressalvas, como pgvector ausente).
  - 503: Unhealthy (quando o banco relacional não responde).
  - 401: Unauthorized (quando X-API-Key não é fornecida ou é inválida).
