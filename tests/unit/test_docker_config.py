"""Testes de validação estática dos arquivos de configuração Docker e Compose."""

from pathlib import Path


def test_dockerfile_exists_and_valid() -> None:
    """Valida se o Dockerfile existe e contém as instruções essenciais."""
    dockerfile_path = Path("docker/Dockerfile")
    assert dockerfile_path.exists(), "Dockerfile não encontrado em docker/Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in content
    assert "COPY --from=ghcr.io/astral-sh/uv:latest" in content
    assert "uv sync" in content
    assert "EXPOSE 8000" in content
    assert "CMD" in content


def test_init_sql_exists_and_valid() -> None:
    """Valida se o script de inicialização do pgvector existe e cria a extensão."""
    init_sql_path = Path("docker/init.sql")
    assert init_sql_path.exists(), "init.sql não encontrado em docker/init.sql"
    content = init_sql_path.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS vector;" in content


def test_docker_compose_exists_and_valid() -> None:
    """Valida se docker-compose.yml possui os serviços lumi-db e lumi-api."""
    compose_path = Path("docker-compose.yml")
    assert compose_path.exists(), "docker-compose.yml não encontrado na raiz"
    content = compose_path.read_text(encoding="utf-8")

    assert "lumi-db:" in content
    assert "pgvector/pgvector:pg16" in content
    assert "lumi-api:" in content
    assert "condition: service_healthy" in content
    assert "lumi_pgdata:" in content


def test_dockerignore_exists() -> None:
    """Valida se o .dockerignore existe e ignora artefatos desnecessários."""
    dockerignore_path = Path(".dockerignore")
    assert dockerignore_path.exists(), ".dockerignore não encontrado"
    content = dockerignore_path.read_text(encoding="utf-8")

    assert ".venv" in content
    assert ".git" in content
    assert "__pycache__" in content
