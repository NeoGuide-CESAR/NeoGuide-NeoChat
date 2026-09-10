# Proposal: Containerização Local com Docker, Docker Compose e pgvector

## Context
A equipe de desenvolvimento do Lumi possui ambientes heterogêneos. A compilação local da extensão `pgvector` no PostgreSQL e as configurações locais podem gerar atritos e inconsistências de setup. Conforme a ADR-05, a solução deve ser executada integralmente via Docker com zero atrito de setup local.

## Motivation & Value
Permitir que qualquer desenvolvedor clone o repositório e inicie o ambiente completo com um único comando (`docker compose up --build`), subindo a API FastAPI com hot-reload e o banco de dados PostgreSQL 16 com a extensão vetorial `pgvector` habilitada automaticamente.

## Scope
### In-Scope
- `docker/Dockerfile`: Multi-stage build otimizado com Python 3.12-slim, instalador de pacotes `uv` e suporte a live reload.
- `docker/init.sql`: Script de inicialização executando `CREATE EXTENSION IF NOT EXISTS vector;`.
- `docker-compose.yml`: Orquestração dos serviços `lumi-api` e `lumi-db` com volumes persistentes, healthcheck e rede integrada.
- `.dockerignore`: Exclusão de arquivos de ambiente virtual, histórico git, pastas de teste e relatórios.
- Testes automatizados para validação de integridade sintática e estrutural dos arquivos de infraestrutura Docker.

### Out-of-Scope
- Orquestração de produção com Kubernetes, Helm ou ECS.
- Configuração de CI/CD para push de imagens em registry remoto.
