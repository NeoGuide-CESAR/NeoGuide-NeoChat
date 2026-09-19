# Lumi (NeoGuide)

Assistente Normativo Inteligente para Infraestrutura de Telecomunicações.

Desenvolvido para engenheiros de campo, projetistas e técnicos de infraestrutura da Neoenergia, o **Lumi** resolve o atrito de consulta a normas técnicas volumosas (DIS-NOR-030 e DIS-NOR-053), fornecendo respostas precisas com embasamento normativo direto, transcrição de tabelas e citação exata de artigos e páginas.

## Stack Tecnológica
- **Linguagem & Runtime:** Python 3.12+ gerenciado por `uv`
- **Framework Web:** FastAPI (com streaming Server-Sent Events e endpoints síncronos)
- **Framework de IA:** LangChain (com Google Gemini como provedor primário e Anthropic Claude como fallback)
- **Persistência & Vetores:** PostgreSQL 16 + pgvector (orquestrado via Docker Compose)
- **Validação & Contratos:** Pydantic v2 & Pydantic Settings
- **Logs Estruturados:** structlog (JSON)
- **Qualidade & Segurança:** pre-commit hooks, Ruff, Mypy e detect-secrets

## Execução Rápida

### 1. Pré-requisitos
- [uv](https://docs.astral.sh/uv/) (versão >= 0.4)
- Docker & Docker Compose

### 2. Configuração do Ambiente
```bash
cp .env.example .env
# Adicione sua chave GEMINI_API_KEY no arquivo .env
```

### 3. Banco de Dados, Migrações e Ingestão de Normas
```bash
# Iniciar o PostgreSQL 16 com pgvector
docker compose up -d lumi-db

# Sincronizar dependências com uv (incluindo testes e linters)
uv sync --extra dev

# Executar as migrações estruturais do banco de dados
uv run alembic upgrade head

# Ingerir e indexar as normas técnicas (DIS-NOR-030 e DIS-NOR-053) no pgvector
uv run python -m lumi.ingestion --path docs/info --all
```

### 4. Execução da API Localmente
```bash
# Executar a API FastAPI com hot-reload
uv run uvicorn src.lumi.main:app --reload --port 8000
```

Documentação interativa disponível em `http://localhost:8000/docs`.

### 5. Execução de Testes e Qualidade
```bash
# Executar suite completa de testes
uv run pytest

# Verificação com linters e checagem de tipos
uv run ruff check .
uv run mypy src
```

> 📖 **Guia Completo:** Para instruções detalhadas com exemplos de cURL, streaming SSE, PowerShell e troubleshooting, consulte o [08. Guia de Configuração e Execução Local](docs/08-CONFIGURACAO-E-EXECUCAO-LOCAL.md).
