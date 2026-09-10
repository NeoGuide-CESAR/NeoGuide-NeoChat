# Spec: Containerização Local e pgvector

## Requirements

### Requirement: Dockerfile Otimizado com uv
O projeto DEVE fornecer um `docker/Dockerfile` baseado em Python 3.12-slim utilizando o binário oficial do `uv` para sincronização reproduzível e rápida de dependências, configurado com hot-reload para ambiente de desenvolvimento.

#### Scenario: Build da Imagem Docker
- **GIVEN** o código do projeto com `pyproject.toml` e `uv.lock`
- **WHEN** o Dockerfile for submetido a build
- **THEN** a imagem deve instalar as dependências sem erros e expor a porta 8000.

### Requirement: Inicialização do pgvector
O serviço de banco de dados DEVE executar na primeira inicialização o comando de criação da extensão vetorial `vector`.

#### Scenario: Script de Inicialização do Banco
- **GIVEN** o script `docker/init.sql` montado em `/docker-entrypoint-initdb.d/init.sql`
- **WHEN** o container do PostgreSQL inicializar
- **THEN** a instrução `CREATE EXTENSION IF NOT EXISTS vector;` deve ser executada com sucesso.

### Requirement: Orquestração com Docker Compose
O projeto DEVE fornecer um `docker-compose.yml` na raiz mapeando os serviços `lumi-api` e `lumi-db`, com controle de ordem de inicialização via healthcheck e persistência em volume local.

#### Scenario: Ordem de Subida dos Serviços
- **GIVEN** o comando `docker compose up`
- **WHEN** os containers forem iniciados
- **THEN** o serviço `lumi-api` deve aguardar o `lumi-db` atingir o status `healthy` antes de iniciar a API.
