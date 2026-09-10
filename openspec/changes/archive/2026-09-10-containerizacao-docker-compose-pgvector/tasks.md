# Tasks: Containerização Local com Docker, Docker Compose e pgvector

## 1. Configurações de Docker e Banco
- [x] 1.1 Criar `docker/init.sql` com instrução `CREATE EXTENSION IF NOT EXISTS vector;`.
- [x] 1.2 Criar `docker/Dockerfile` multi-stage com Python 3.12, `uv` e suporte a live reload.
- [x] 1.3 Criar `.dockerignore` com exclusões pertinentes.

## 2. Orquestração Docker Compose
- [x] 2.1 Criar `docker-compose.yml` integrando `lumi-api` e `lumi-db` (pgvector).
- [x] 2.2 Configurar healthcheck, volumes persistentes e dependências entre serviços.

## 3. Verificação e Testes
- [x] 3.1 Criar teste automatizado em `tests/unit/test_docker_config.py` validando integridade e sintaxe dos arquivos.
- [x] 3.2 Executar testes automatizados via `pytest`.
