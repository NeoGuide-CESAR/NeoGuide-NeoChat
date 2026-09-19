# 08. Guia de Configuração e Execução Local — Lumi (NeoGuide)

Este documento fornece um passo a passo completo, detalhado e reproduzível para configurar o ambiente de desenvolvimento, inicializar os serviços de banco de dados vetorial, executar migrações, realizar a ingestão das normas técnicas e rodar a API do **Lumi** localmente.

---

## 1. Visão Geral da Arquitetura Local

Para que a Lumi funcione localmente em sua plenitude, os seguintes componentes interagem:

```mermaid
graph TD
    User["Desenvolvedor / Cliente HTTP (cURL / Swagger / Frontend)"]
    API["FastAPI App (uvicorn src.lumi.main:app) :8000"]
    DB[("PostgreSQL 16 + pgvector :5432\n(Container Docker: lumi-db)")]
    LLM["Provedor de IA Externo\n(Google Gemini / Anthropic Claude)"]
    Docs["Normas Técnicas (docs/info/)\nDIS-NOR-030 & DIS-NOR-053"]

    User -->|"HTTP / SSE (Header: X-API-Key)"| API
    API -->|"SQLAlchemy Async + asyncpg"| DB
    API -->|"Consultas Vetoriais (HNSW Cosine)"| DB
    API -->|"Geração de Resposta / Rerank"| LLM
    Docs -->|"CLI de Ingestão (python -m lumi.ingestion)"| API
    API -->|"Embeddings Vetoriais (768d)"| LLM
    API -->|"Persistência de Chunks & Vetores"| DB
```

---

## 2. Pré-requisitos de Sistema

Antes de iniciar, certifique-se de possuir instalados em seu sistema operacional:

1. **Python 3.12 ou superior**:
   - Verifique com: `python --version` ou `python3 --version`.
2. **uv (Gerenciador de Pacotes e Ambientes Python ultrarrápido)**:
   - Instalação oficial:
     - **Windows (PowerShell):**
       ```powershell
       powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
       ```
     - **Linux / macOS:**
       ```bash
       curl -LsSf https://astral.sh/uv/install.sh | sh
       ```
   - Verifique com: `uv --version` (requerido >= 0.4.0).
3. **Docker e Docker Compose**:
   - Necessário para executar o PostgreSQL 16 compilado com a extensão `pgvector`.
   - Verifique com: `docker --version` e `docker compose version`.
4. **Git**:
   - Para controle de versão e hooks de pre-commit.
5. **Chave de API do Google Gemini (Obrigatória para IA e Embeddings)**:
   - Obtenha gratuitamente ou via Google AI Studio em: [aistudio.google.com](https://aistudio.google.com/).
   - *(Opcional)* Chave da Anthropic Claude se desejar utilizar o provedor secundário de fallback.

---

## 3. Passo a Passo de Configuração

### Passo 1: Navegar até a Raiz do Repositório

```bash
cd /caminho/para/lumi-neoguide
```

---

### Passo 2: Configurar as Variáveis de Ambiente (`.env`)

Copie o arquivo de modelo `.env.example` para criar o seu `.env` local:

- **Linux / macOS:**
  ```bash
  cp .env.example .env
  ```
- **Windows (PowerShell):**
  ```powershell
  Copy-Item .env.example .env
  ```
- **Windows (CMD):**
  ```cmd
  copy .env.example .env
  ```

Abra o arquivo `.env` gerado no seu editor e configure as variáveis essenciais:

```dotenv
# =============================================================================
# Lumi (NeoGuide) — Variáveis Locais
# =============================================================================

# --- API & Servidor ---
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
API_KEY=lumi-dev-secret-key-change-in-production

# --- Banco de Dados & Vetores (PostgreSQL 16 + pgvector) ---
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_db
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30

# --- Provedores de LLM & IA ---
DEFAULT_LLM_PROVIDER=gemini
DEFAULT_EMBEDDING_PROVIDER=gemini

# Google Gemini (OBRIGATÓRIO: insira sua chave válida aqui)
GEMINI_API_KEY=AIzaSy_SUA_CHAVE_REAL_AQUI
GEMINI_MODEL=gemini-1.5-pro
GEMINI_EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSION=768

# Anthropic Claude (Opcional - Provedor de Fallback)
ANTHROPIC_API_KEY=sk-ant-SUA_CHAVE_OPCIONAL_AQUI
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# --- RAG & Recuperação Vetorial ---
SIMILARITY_THRESHOLD=0.70
TOP_K_RETRIEVAL=10
RERANKER_ENABLED=true
RERANKER_TOP_N=5
QUERY_REWRITER_ENABLED=true

# --- Sessões & Rate Limiting ---
SESSION_TTL_HOURS=1
CHAT_HISTORY_LIMIT=10
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

> [!IMPORTANT]
> A variável `GEMINI_API_KEY` deve conter uma chave válida para que o pipeline de embeddings e a geração de respostas com RAG funcionem. Caso não fornecida, as operações de vetorização com o provedor `gemini` retornarão erro de autenticação.

---

### Passo 3: Inicializar o Banco de Dados com Docker (pgvector)

Suba o container do banco de dados PostgreSQL 16 com suporte nativo à extensão vetorial:

```bash
docker compose up -d lumi-db
```

Para verificar se o container está saudável (`healthy`) e operante:

```bash
docker compose ps
```

O container `lumi-db` executará o script de inicialização `docker/init.sql`, garantindo que a extensão `vector` seja ativada no banco `lumi_db`.

---

### Passo 4: Instalar as Dependências do Projeto via `uv`

Com o `uv`, a criação do ambiente virtual (`.venv`) e a resolução de dependências ocorrem de forma atômica e instantânea:

```bash
# Sincroniza as dependências do projeto e ferramentas de desenvolvimento (pytest, ruff, mypy):
uv sync --extra dev
```

> [!TIP]
> Se desejar instalar apenas as dependências mínimas de execução da API (sem testes ou linters), basta rodar `uv sync`. O grupo opcional `evals` (Ragas) exige compilação C++ e é restrito a benchmarks offline.

Isso instalará FastAPI, Uvicorn, SQLAlchemy, Alembic, LangChain, Google GenAI, Anthropic, Pytest, Ruff, Mypy e demais dependências declaradas no `pyproject.toml`.

---

### Passo 5: Executar as Migrações do Banco de Dados (Alembic)

Com o banco de dados ativo, aplique as migrações estruturais para criar as tabelas de normas (`normative_documents`), fragmentos vetoriais (`normative_chunks`), sessões de chat (`chat_sessions`) e mensagens (`chat_messages`), bem como os índices HNSW:

```bash
uv run alembic upgrade head
```

Você verá a saída confirmando a criação das tabelas e índices:
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Generating static SQL / applying migrations...
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema, Criacao do schema relacional e vetorial inicial
```

---

### Passo 6: Ingestão e Indexação das Normas Técnicas no pgvector

O Lumi necessita que os documentos normativos estejam fatiados e indexados no banco vetorial para responder às dúvidas dos usuários com embasamento técnico e citação exata de artigos e páginas.

O repositório já inclui as normas técnicas oficiais da Neoenergia no diretório `docs/info/`:
- **DIS-NOR-030-REV07** (Norma de Compartilhamento de Postes e Faixa de Ocupação de Telecomunicações)
- **DIS-NOR-053-REV06** (Critérios de Projeto de Redes Aéreas e Telecomunicações)

Execute o pipeline de ingestão para ler, sanitizar, fatiar em chunks estruturados, gerar embeddings (via Google Gemini) e criar o índice vetorial no PostgreSQL:

```bash
# Ingestão de todos os documentos normativos presentes em docs/info:
uv run python -m lumi.ingestion --path docs/info --all
```

Ou, se desejar ingerir um documento específico individualmente:

```bash
uv run python -m lumi.ingestion --path docs/info/DIS-NOR-030-REV07.md
```

Ao término, você verá uma saída detalhando os chunks indexados:
```text
[INICIANDO] Ingestão normativa de 2 arquivo(s)...
[CONFIG] Provedor: gemini | Batch size: 32

[PROCESSANDO] DIS-NOR-030-REV07.md ... [OK] Concluído! Norma: DIS-NOR-030 (Rev: REV07) - 48 chunks indexados em 4.2s
[PROCESSANDO] DIS-NOR-053-REV06.md ... [OK] Concluído! Norma: DIS-NOR-053 (Rev: REV06) - 35 chunks indexados em 3.5s

[CONCLUÍDO] Pipeline finalizado!
```

---

### Passo 7: Iniciar o Servidor Web FastAPI

Agora que o banco está migrado e com as normas indexadas, inicie o servidor da API com recarregamento automático (*Hot-Reload*):

```bash
uv run uvicorn src.lumi.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará acessível em:
- **URL Base:** `http://localhost:8000`
- **Swagger UI Interativo (OpenAPI):** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 4. Alternativa: Execução 100% via Docker Compose

Se preferir rodar toda a aplicação (API + Banco de dados) conteinerizada sem depender de Python instalado no host:

```bash
# Constrói a imagem da API e sobe todos os serviços:
docker compose up --build
```

Para rodar em segundo plano:
```bash
docker compose up -d --build
```

Para aplicar as migrações e ingestão dentro do container da API:
```bash
docker compose exec lumi-api uv run alembic upgrade head
docker compose exec lumi-api uv run python -m lumi.ingestion --path docs/info --all
```

Para derrubar os containers:
```bash
docker compose down
```

---

## 5. Como Testar e Interagir com a API

### 5.1. Verificação de Saúde (Health Check)

Verifica se a aplicação está online:

- **cURL:**
  ```bash
  curl -X GET http://localhost:8000/health
  ```
- **Resposta esperada (HTTP 200):**
  ```json
  {
    "status": "healthy",
    "version": "0.1.0"
  }
  ```

---

### 5.2. Verificação de Autenticação

Testa se sua `API_KEY` configurada no `.env` está sendo aceita pelo middleware de segurança:

- **cURL:**
  ```bash
  curl -X GET http://localhost:8000/api/v1/auth/check \
    -H "X-API-Key: lumi-dev-secret-key-change-in-production"
  ```
- **Resposta esperada (HTTP 200):**
  ```json
  {
    "status": "authenticated",
    "message": "API Key is valid"
  }
  ```

---

### 5.3. Criando uma Sessão de Conversa

Toda interação conversacional com a Lumi deve pertencer a uma sessão:

- **cURL (Linux / macOS / Git Bash):**
  ```bash
  curl -X POST http://localhost:8000/api/v1/sessions \
    -H "Content-Type: application/json" \
    -H "X-API-Key: lumi-dev-secret-key-change-in-production"
  ```
- **PowerShell (Windows):**
  ```powershell
  $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sessions" `
    -Method Post `
    -Headers @{ "X-API-Key" = "lumi-dev-secret-key-change-in-production" }
  $sessionId = $response.id
  Write-Output "Sessão criada: $sessionId"
  ```
- **Resposta esperada (HTTP 201):**
  ```json
  {
    "id": "c1a93b48-8ef8-498c-9a4f-56ec0409bb10",
    "created_at": "2026-09-17T03:50:00Z"
  }
  ```

---

### 5.4. Enviando uma Pergunta Normativa (Resposta Síncrona)

Envie uma dúvida técnica sobre as normas de telecomunicação da Neoenergia com `stream: false`:

- **cURL:**
  ```bash
  curl -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -H "X-API-Key: lumi-dev-secret-key-change-in-production" \
    -d '{
      "session_id": "c1a93b48-8ef8-498c-9a4f-56ec0409bb10",
      "message": "Qual é a faixa de ocupação permitida para cabos de telecomunicações no poste?",
      "stream": false
    }'
  ```
- **PowerShell (Windows):**
  ```powershell
  $body = @{
      session_id = $sessionId
      message    = "Qual é a faixa de ocupação permitida para cabos de telecomunicações no poste?"
      stream     = $false
  } | ConvertTo-Json

  Invoke-RestMethod -Uri "http://localhost:8000/api/v1/chat" `
    -Method Post `
    -Headers @{
        "Content-Type" = "application/json"
        "X-API-Key"    = "lumi-dev-secret-key-change-in-production"
    } `
    -Body $body
  ```
- **Resposta esperada (HTTP 200):**
  ```json
  {
    "session_id": "c1a93b48-8ef8-498c-9a4f-56ec0409bb10",
    "response": "De acordo com a norma DIS-NOR-030, a faixa de ocupação destinada ao compartilhamento com redes de telecomunicações é de 500 mm...",
    "sources": [
      {
        "document_code": "DIS-NOR-030",
        "revision": "REV07",
        "section": "Item 5.2 - Faixa de Ocupação",
        "page": 12,
        "relevance_score": 0.89,
        "snippet": "A faixa de ocupação destinada aos pontos de fixação das redes de telecomunicações é delimitada em 500 mm..."
      }
    ]
  }
  ```

---

### 5.5. Enviando Mensagem com Streaming em Tempo Real (SSE)

Para uma experiência interativa token a token (Server-Sent Events):

- **cURL:**
  ```bash
  curl -N -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -H "X-API-Key: lumi-dev-secret-key-change-in-production" \
    -d '{
      "session_id": "c1a93b48-8ef8-498c-9a4f-56ec0409bb10",
      "message": "Qual a distância de segurança em relação aos condutores de baixa tensão?",
      "stream": true
    }'
  ```

Eventos emitidos no stream SSE:
1. `event: metadata` (fontes recuperadas e IDs)
2. `event: token` (fragmentos de texto transmitidos progressivamente)
3. `event: done` (término do streaming e sumário)

---

## 6. Comandos de Qualidade, Testes e Linting

O repositório possui suíte de testes automatizados e linters configurados:

```bash
# 1. Executar todos os testes unitários e de integração:
uv run pytest

# 2. Executar testes com relatório de cobertura de código:
uv run pytest --cov=src/lumi --cov-report=term-missing

# 3. Executar verificações de formatação e linting com Ruff:
uv run ruff check .
uv run ruff format --check .

# 4. Executar checagem estática rigorosa de tipos com Mypy:
uv run mypy src

# 5. Instalar e rodar os hooks de pre-commit no Git:
uv run pre-commit install
uv run pre-commit run --all-files
```

---

## 7. Resolução de Problemas Comuns (Troubleshooting)

### 1. "Port 5432 is already in use"
- **Causa:** Há outra instância do PostgreSQL instalada localmente no sistema operacional ocupando a porta 5432.
- **Solução:**
  - Pare o PostgreSQL local (`net stop postgresql` no Windows ou `sudo systemctl stop postgresql` no Linux) ou
  - Altere a porta mapeada no `docker-compose.yml` para `"5433:5432"` e ajuste a `DATABASE_URL` no `.env` para apontar para a porta `5433`.

### 2. "extension 'vector' does not exist"
- **Causa:** O banco de dados foi inicializado a partir de uma imagem padrão do Postgres sem o pgvector compilado.
- **Solução:** Use estritamente a imagem oficial configurada no `docker-compose.yml`: `pgvector/pgvector:pg16`. Se o volume foi criado anteriormente sem ela, resete o volume com `docker compose down -v` e recrie com `docker compose up -d lumi-db`.

### 3. "401 Unauthorized: Invalid or missing API Key"
- **Causa:** A requisição HTTP não incluiu o cabeçalho `X-API-Key` ou enviou uma chave diferente daquela definida na variável `API_KEY` do arquivo `.env`.
- **Solução:** Certifique-se de incluir o cabeçalho `X-API-Key: <valor_do_seu_.env>` em todas as requisições para `/api/v1/*`.

### 4. "429 Too Many Requests: Rate limit exceeded"
- **Causa:** O cliente ultrapassou o limite de requisições por minuto configurado.
- **Solução:** O valor padrão é 60 requisições/minuto. Para desenvolvimento, você pode elevar esse limite alterando `RATE_LIMIT_REQUESTS_PER_MINUTE=600` no seu `.env`.

### 5. "Falha ao gerar embeddings: Google API Key is invalid"
- **Causa:** A variável `GEMINI_API_KEY` está com o valor padrão de exemplo do `.env.example`.
- **Solução:** Gere uma chave gratuita no [Google AI Studio](https://aistudio.google.com/) e atualize o `.env`.

---

## 8. Resumo dos Comandos Mais Utilizados

| Operação | Comando |
| :--- | :--- |
| **Subir Banco de Dados** | `docker compose up -d lumi-db` |
| **Instalar Dependências** | `uv sync --all-extras` |
| **Aplicar Migrações** | `uv run alembic upgrade head` |
| **Ingerir Normas Técnicas** | `uv run python -m lumi.ingestion --path docs/info --all` |
| **Iniciar a API (Dev)** | `uv run uvicorn src.lumi.main:app --reload --port 8000` |
| **Rodar Testes** | `uv run pytest` |
| **Validar Qualidade / Linters**| `uv run ruff check . && uv run mypy src` |
| **Acessar Documentação Swagger**| Abra `http://localhost:8000/docs` no navegador |
