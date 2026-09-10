# Proposal: Setup do Ambiente Python com uv e pyproject.toml

## Context
O Lumi (NeoGuide) é um assistente normativo inteligente para infraestrutura de telecomunicações que utiliza FastAPI, LangChain, PostgreSQL com pgvector, Pydantic v2 e estruturação de dados em Python 3.12+. Para garantir instalações determinísticas e rápidas sem conflito de resolução de dependências pesadas de IA, o time adotou o gerenciador de pacotes `uv` (ADR-02) em vez de Poetry/Pipenv.

## Motivation & Value
Estabelecer a configuração padrão do pacote Python (`lumi`) via `pyproject.toml`, unificando a declaração de dependências de produção e de desenvolvimento, gerando a trava `uv.lock` e fornecendo um arquivo `.env.example` completo com todas as variáveis essenciais descritas nos documentos de requisitos e arquitetura.

## Scope
### In-Scope
- Criação e configuração de `pyproject.toml` compatível com PEP 517/518/621, usando o build backend `hatchling` e gerenciado pelo `uv`.
- Definição de dependências principais: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy[asyncio]`, `asyncpg`, `pgvector`, `langchain`, `langchain-google-genai`, `langchain-anthropic`, `structlog`.
- Definição de dependências de desenvolvimento: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `pre-commit`.
- Configuração de ferramentas no `pyproject.toml`: `ruff`, `mypy`, `pytest`.
- Criação da estrutura inicial do pacote em `src/lumi/` com `main.py` contendo uma aplicação FastAPI básica funcional.
- Criação de `tests/` com conftest e teste de smoke validando a inicialização da API.
- Criação de `.env.example` documentando as variáveis de ambiente.
- Geração de `uv.lock`.

### Out-of-Scope
- Configuração de containers Docker (coberto por TECH-02).
- Configuração de hooks git pre-commit (coberto por TECH-04).
- Modelos ORM completos e migrações Alembic (coberto por TECH-03).
