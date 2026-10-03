# Lumi (NeoGuide)

Assistente Normativo Inteligente para Infraestrutura de Telecomunicações.

Desenvolvido para engenheiros de campo, projetistas e técnicos de infraestrutura da Neoenergia, o **Lumi** resolve o atrito de consulta a normas técnicas volumosas (DIS-NOR-030 e DIS-NOR-053), fornecendo respostas precisas com embasamento normativo direto, transcrição de tabelas e citação exata de artigos e páginas.

## Stack Tecnológica
- **Linguagem & Runtime:** Python 3.12+ gerenciado por `uv`
- **Framework Web:** FastAPI (com streaming Server-Sent Events e endpoints síncronos)
- **Framework de IA:** LangChain (Google Gemini primário com cadeia de fallback de modelos)
- **Persistência & Vetores:** PostgreSQL 16 + pgvector (orquestrado via Docker Compose com dados persistidos em `./docker/data`)
- **Validação & Contratos:** Pydantic v2 & Pydantic Settings
- **Logs Estruturados:** structlog (JSON)
- **Qualidade & Segurança:** pre-commit hooks, Ruff, Mypy e detect-secrets

---

## Execução Rápida

### 1. Pré-requisitos
- [Docker & Docker Compose](https://www.docker.com/)
- [uv](https://docs.astral.sh/uv/) (versão >= 0.4) *(opcional para execução local fora de containers)*

### 2. Configuração do Ambiente
Copie o modelo de variáveis de ambiente e insira sua chave da API do Google Gemini:
```bash
cp .env.example .env
# Preencha a variável GEMINI_API_KEY no arquivo .env
```

### 3. Subindo a Aplicação
Como o banco de dados vetorial já está pré-carregado e indexado em `./docker/data`, basta subir a stack:
```bash
# Iniciar a API e o PostgreSQL 16 com pgvector em segundo plano
docker compose up -d

# Verificar se os containers estão saudáveis
docker compose ps
```

> **Para encerrar os containers:**
> ```bash
> docker compose down
> ```

---

## Testando a API Localmente

Com os containers em execução, a API estará acessível em `http://localhost:8000`:

- **Swagger UI (Documentação Interativa & Testes):**
  Acesse [http://localhost:8000/docs](http://localhost:8000/docs) para inspecionar endpoints, esquemas de entrada/saída e testar requisições diretamente pelo navegador.
- **ReDoc (Documentação de Referência):**
  Acesse [http://localhost:8000/redoc](http://localhost:8000/redoc) para visualizar a especificação OpenAPI formatada para leitura técnica.
- **Verificação de Saúde (Health Check):**
  ```bash
  curl http://localhost:8000/health
  # Resposta esperada: {"status":"healthy","version":"0.1.0"}
  ```
- **Consulta Normativa (Chat):**
  Endpoint `POST /api/v1/chat/completions` com suporte a respostas síncronas e streaming SSE (`text/event-stream`).

---

## Comandos Úteis com `uv` (Desenvolvimento Local)

Para desenvolvedores que queiram rodar a API, migrações ou testes fora do container:

```bash
# Sincronizar dependências do projeto (incluindo pacotes de dev)
uv sync --extra dev

# Executar a API localmente com hot-reload (requer lumi-db em execução)
uv run uvicorn src.lumi.main:app --reload --port 8000

# Executar a suíte de testes automatizados
uv run pytest

# Executar apenas testes rápidos (ignorando integrações e chamadas a LLMs)
uv run pytest -m "not integration and not evals"

# Checagem e formatação com Ruff
uv run ruff check .
uv run ruff format .

# Checagem estática de tipos com Mypy
uv run mypy src
```

---

## Scripts de Ingestão Normativa

> 💡 **Nota:** O banco de dados versionado em `docker/data` já contém os chunks e embeddings das normas DIS-NOR-030 e DIS-NOR-053 devidamente indexados. Utilize os scripts abaixo caso deseje atualizar uma norma ou indexar novos arquivos normativos.

```bash
# Ingerir e indexar todas as normas presentes em docs/info/
uv run python -m lumi.ingestion --path docs/info --all

# Ingerir um documento específico (.md ou .pdf)
uv run python -m lumi.ingestion docs/info/DIS-NOR-030-REV07.md

# Testar o pipeline de ingestão com embeddings simulados (sem consumir cota de IA)
uv run python -m lumi.ingestion docs/info/DIS-NOR-030-REV07.md --provider fake
```

---

## Documentação Técnica

Para detalhes aprofundados sobre arquitetura, modelagem, segurança e decisões de projeto, consulte os documentos em [`docs/`](docs/):

- [01. Visão do Projeto](docs/01-VISAO.md) — Objetivos de negócio, personas e justificativa da solução.
- [02. Requisitos](docs/02-REQUISITOS.md) — Requisitos funcionais (RF), não funcionais (RNF) e critérios de aceitação.
- [03. Modelagem de Domínio](docs/03-MODELAGEM.md) — Entidades, agregados e modelo de persistência no PostgreSQL.
- [04. Fluxos do Sistema](docs/04-FLUXOS.md) — Diagramas de sequência para chat síncrono, streaming SSE e ingestão.
- [05. Arquitetura do Sistema](docs/05-ARQUITETURA.md) — Arquitetura técnica C4, componentes e padrões de resiliência.
- [06. Estrutura de Pastas e Convenções](docs/06-ESTRUTURA-DE-PASTAS.md) — Padrões arquiteturais de pastas, módulos e convenções de código.
- [07. Segurança e Avaliação de IA](docs/07-SEGURANCA-E-AVALIACAO-IA.md) — Guardrails, mitigação de injeção de prompt e framework de Evals (Ragas).
- [08. Guia de Configuração e Execução Local](docs/08-CONFIGURACAO-E-EXECUCAO-LOCAL.md) — Manual completo com exemplos de cURL, streaming SSE e troubleshooting.
- [09. Relatório de Revisão Técnica](docs/09-RELATORIO-DE-REVISAO-TECNICA.md) — Comparativo entre planejamento arquitetural e implementação entregue.
