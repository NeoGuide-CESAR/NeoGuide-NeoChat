# =============================================================================
# Lumi (NeoGuide) — Dockerfile Multi-stage com Python 3.12 & uv
# =============================================================================

# --- Estágio 1: Base de Execução e Dependências ---
FROM python:3.12-slim AS base

# Instalar utilitários essenciais
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copiar o binário estático do uv da imagem oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Configurações de ambiente Python e uv
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/app/.venv/bin:$PATH"

# Copiar arquivos de definição e trava de dependências primeiro (cache eficiente)
COPY pyproject.toml uv.lock ./

# Instalar dependências sem instalar o projeto (otimização de cache de camadas)
RUN uv sync --frozen --no-install-project --no-dev

# Copiar o restante do código fonte da aplicação
COPY README.md ./
COPY src/ ./src/

# Instalar o pacote lumi no ambiente
RUN uv sync --frozen --no-dev

# Criar usuário não-root para segurança
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Comando padrão para ambiente de desenvolvimento com live reload
CMD ["uv", "run", "uvicorn", "src.lumi.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
