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
```

### 3. Instalação de Dependências e Execução Local
```bash
# Sincronizar dependências com uv
uv sync

# Executar a API localmente
uv run uvicorn src.lumi.main:app --reload --port 8000
```

### 4. Execução de Testes
```bash
uv run pytest
```
