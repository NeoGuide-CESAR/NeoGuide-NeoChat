# Proposal: Logging Estruturado com structlog, Correlação por X-Request-ID e Mascaramento de Dados Sensíveis

## Context
A API Lumi (NeoGuide) orquestra consultas assíncronas de engenharia normativa, integrando camadas de roteamento HTTP, RAG com busca vetorial no PostgreSQL/pgvector e inferências em modelos de linguagem externos (Google Gemini e Anthropic Claude).
Em ambientes distribuídos e de produção, o rastreamento ponta a ponta de requisições e a integridade da auditoria operacional demandam um formato padronizado de logs (JSON em produção, colorido em desenvolvimento) e correlação inequívoca de contexto assíncrono via `X-Request-ID`.
Adicionalmente, requisitos regulatórios e de segurança (RNF-11 / RNF-12) impõem que credenciais, chaves de API, senhas e tokens nunca sejam vazados nos arquivos ou fluxos de log.

## Motivation & Value
1. **Observabilidade Estruturada**: Substituição de logs textuais não estruturados por eventos em JSON machine-readable em ambientes produtivos/staging e formatação visual em desenvolvimento.
2. **Correlação Assíncrona de Requisições**: Injeção e propagação de identificadores de correlação (`X-Request-ID`) em cada requisição HTTP, permitindo filtrar e correlacionar todas as entradas de log de uma transação específica via `contextvars`.
3. **Segurança e Blindagem contra Vazamento (Redaction)**: Interceptação defensiva na pipeline de processamento do structlog para mascarar recursivamente quaisquer valores associados a chaves sensíveis (`api_key`, `authorization`, `password`, `token`, etc.) antes da escrita.
4. **Unificação com Logs da Standard Library**: Interceptação dos logs gerados pelo Uvicorn (`uvicorn`, `uvicorn.access`, `uvicorn.error`) e SQLAlchemy (`sqlalchemy.engine`) canalizando-os através dos processadores e renderizadores do structlog.

## Scope

### In-Scope
- Criação do módulo `src/lumi/core/logging.py`:
  - Implementação de `setup_logging(environment: str | None = None, log_level: str | None = None)`.
  - Processador `redact_sensitive_data` com sanitização recursiva case-insensitive.
  - Configuração de processadores padrão do structlog (`merge_contextvars`, `add_log_level`, `TimeStamper`, `StackInfoRenderer`, `format_exc_info`).
  - Alternância de renderizador: `JSONRenderer` em produção/staging, `ConsoleRenderer(colors=True)` nos demais.
  - Integração unificada com stdlib (`logging.basicConfig` e `ProcessorFormatter`) para rotear logs do Uvicorn e SQLAlchemy.
- Criação do módulo `src/lumi/api/middleware.py`:
  - Implementação do `CorrelationIdMiddleware(BaseHTTPMiddleware)`.
  - Extração ou geração de `X-Request-ID` (UUIDv4).
  - Associação via `structlog.contextvars.bind_contextvars`.
  - Injeção do header `X-Request-ID` na resposta HTTP.
  - Emissão de logs estruturados de início e fim da requisição com métricas de tempo (`duration_ms`), status HTTP, método e caminho.
  - Limpeza contextual segura via `structlog.contextvars.clear_contextvars()` em bloco `finally`.
- Integração no ciclo de vida em `src/lumi/main.py`:
  - Invocação de `setup_logging()` antes da inicialização do `FastAPI`.
  - Registro de `CorrelationIdMiddleware` no app FastAPI.
- Cobertura com testes unitários em `tests/unit/test_logging.py`.

### Out-of-Scope
- Exportação direta via OTLP / OpenTelemetry collector (reservado para futuras fases de APM).
- Rotação física de arquivos de log em disco (delegada para orquestradores de contêineres / stdout).
