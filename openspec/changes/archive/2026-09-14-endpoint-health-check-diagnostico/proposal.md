# Proposal: Endpoint de Health Check e Diagnóstico de Conectividade

## Context
A plataforma Lumi (NeoGuide) opera como um assistente normativo inteligente com arquitetura RAG (Retrieval-Augmented Generation). O serviço depende criticamente de conectividade em tempo real com o banco de dados relacional PostgreSQL e a extensão vetorial `pgvector` para indexação e recuperação semântica de chunks normativos das normas técnicas (ex.: DIS-NOR-030 e DIS-NOR-053). 

Em ambientes de produção e orquestração de contêineres (Kubernetes, Docker Swarm ou ECS), mecanismos automatizados exigem sondas (probes) distintas de integridade:
- **Liveness Probe**: Para verificar se o processo da aplicação HTTP está vivo e respondendo a requisições básicas.
- **Readiness Probe / Diagnóstico Operacional**: Para inspecionar se as dependências operacionais vitais (PostgreSQL, pooling de conexões e suporte a vetores `pgvector`) estão disponíveis e com latências aceitáveis antes de direcionar tráfego de produção.

## Motivation & Value
1. **Diferenciação Clara entre Liveness e Readiness**: O endpoint `/health` público na raiz já fornece liveness leve sem autenticação para balanceadores de carga e orquestradores de contêiner. No entanto, faltava uma sonda aprofundada de conectividade operacional.
2. **Diagnóstico Ativo de Banco e pgvector**: Um endpoint administrativo `/api/v1/health` que valida ativamente um ciclo de consulta (`SELECT 1`), calcula a latência de round-trip em milissegundos e confirma a presença e versão da extensão `pgvector`.
3. **Segurança e Proteção de Informações Sensíveis**: Endpoints de diagnóstico avançado expõem detalhes internos de infraestrutura. Por isso, `/api/v1/health` deve ser protegido por `X-API-Key` e rate limiting, além de garantir que quaisquer exceções de banco sejam interceptadas e sanitizadas defensivamente, nunca vazando credenciais em logs ou respostas HTTP 503.
4. **Modularização da API v1**: Estabelecer a arquitetura de roteamento `api/v1` (`src/lumi/api/v1/router.py`) para organizar endpoints de versão de forma desacoplada e manutenível.

## Scope

### In-Scope
- Manutenção do endpoint GET `/health` na raiz sem autenticação para liveness probe.
- Criação dos schemas Pydantic v2 em `src/lumi/schemas/health.py`:
  - `DatabaseHealthInfo`: status (`connected`, `disconnected`, `error`), latência (`latency_ms`), flag `pgvector_installed`, `pgvector_version` e `error`.
  - `HealthCheckResponse`: status geral (`healthy`, `unhealthy`, `degraded`), versão, ambiente, timestamp UTC e detalhamento `database`.
- Criação da infraestrutura assíncrona de banco de dados em `src/lumi/db/session.py`, fornecendo gerador de sessão `get_db_session` desacoplado e injetável.
- Criação do roteador modular `src/lumi/api/v1/health.py` e agregador `src/lumi/api/v1/router.py`.
- Integração do roteador `api_v1_router` em `src/lumi/main.py` sob o prefixo `/api/v1`.
- Proteção de `GET /api/v1/health` via dependência `api_key_and_rate_limit`.
- Tratamento defensivo de erros com retorno HTTP 503 quando o banco for inacessível.
- Cobertura de testes unitários abrangente em `tests/unit/test_health.py`.

### Out-of-Scope
- Diagnóstico de provedores externos de LLM (Gemini/Claude) com chamadas ativas de tokenização (para evitar custos em probes frequentes).
- Migrações automáticas de schema do banco nesta task (tratado em tarefas dedicadas com Alembic).
