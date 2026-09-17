# Proposal: Persistência Desacoplada Assíncrona de Mensagens e Telemetria Analítica (FEAT-13)

## Context
O Lumi NeoGuide é o assistente inteligente de normas técnicas da Neoenergia Pernambuco.
Na versão anterior (FEAT-11), o fluxo de chat em streaming e síncrono realizava a persistência das respostas do assistente de forma síncrona ou acoplada à sessão do request HTTP.
Para cumprir rigorosamente com a decisão arquitetural ADR-04 (Persistência Desacoplada e Gravação Assíncrona de Histórico) e garantir latência zero de escrita de I/O na entrega ao cliente (RNF-01 e RNF-02), o sistema necessita desacoplar a gravação da mensagem do assistente e os dados de telemetria analítica (`normative_query_analytics`) em rotinas assíncronas em segundo plano com sessões de banco independentes.

## Motivation & Value
1. **Latência Zero de I/O na Entrega ao Usuário (RNF-01, RNF-02, ADR-04)**: No fluxo SSE, a mensagem completa e os dados analíticos são despachados após o evento `done`, garantindo que o cliente receba a totalidade dos tokens e o encerramento sem bloqueios de banco de dados. No modo síncrono, a persistência é despachada via `FastAPI BackgroundTasks`.
2. **Isolamento de Conexões e Sessões de Banco**: Como a sessão HTTP do SQLAlchemy é fechada ao término da resposta, workers em background devem operar com uma sessão independente aberta via `get_db_session()`.
3. **Telemetria Analítica e Auditoria Acadêmica**: Registro automático de latência de resposta em ms, norma principal recuperada, similaridade máxima de cosseno e histórico de perguntas na tabela `normative_query_analytics`.
4. **Resiliência e Tolerância a Falhas**: Mecanismo de 1 retentativa automática com backoff de 500ms sob falhas temporárias de concorrência ou conexão no PostgreSQL, com logs estruturados no `structlog` e sem propagação de erro para a resposta do usuário.
5. **Cobertura de Todos os Ramos do Chat**: Suporte unificado para RAG com sucesso, respostas de contingência normativa (RF-06) e recusas de segurança por guardrails de entrada.

## Scope

### In-Scope
- `src/lumi/services/analytics_service.py`:
  - Classe `AnalyticsService` para registro em `normative_query_analytics`.
  - Função assíncrona `persist_interaction_background`:
    - Abertura de sessão de banco independente via `get_db_session()`.
    - Persistência de `ChatMessage` (role `assistant`, fontes JSONB, atualização de `ChatSession.updated_at`).
    - Persistência de `NormativeQueryAnalytics` (session_id, query_text, top_document_code, top_similarity_score, latency_ms).
    - Tolerância a falhas: 1 retentativa com backoff de 500ms e logs via `structlog`.
- `src/lumi/services/chat_service.py`:
  - Medição de latência fim a fim (`latency_ms`).
  - Despacho em background pós-evento `done` no `stream_chat`.
  - Suporte ao agendamento de background no `process_chat` (via `BackgroundTasks` ou fallback assíncrono).
  - Cobertura dos fluxos: RAG bem-sucedido, contingência normativa e recusa por guardrails.
- `src/lumi/api/v1/chat.py`:
  - Injeção de dependência `background_tasks: BackgroundTasks` no endpoint `POST /api/v1/chat`.
  - Encaminhamento de `background_tasks` para processamento síncrono.
- Testes:
  - Unitários em `tests/unit/test_analytics_service.py`.
  - Integração em `tests/integration/test_chat_background_persistence.py`.
  - Atualização dos testes unitários em `tests/unit/test_chat_service.py`.

### Out-of-Scope
- Filas distribuídas externas como Celery, RabbitMQ ou Redis (o MVP adota asyncio e FastAPI BackgroundTasks conforme RNF-05).
- Dashboards de visualização de métricas (serão consumidos futuramente via consultas SQL ou ferramentas BI).
