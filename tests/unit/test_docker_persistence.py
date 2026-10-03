"""Testes de validação da persistência do Docker via bind mount no repositório (TECH-09)."""

from pathlib import Path


def test_docker_compose_bind_mount_persistence() -> None:
    """Valida se docker-compose.yml configura bind mount para o banco de dados."""
    compose_path = Path("docker-compose.yml")
    assert compose_path.exists(), "docker-compose.yml não encontrado na raiz"
    content = compose_path.read_text(encoding="utf-8")

    assert "./docker/data:/var/lib/postgresql/data" in content, (
        "Bind mount './docker/data:/var/lib/postgresql/data' não encontrado em docker-compose.yml"
    )
    assert "lumi_pgdata" not in content, (
        "Volume nomeado 'lumi_pgdata' ainda está presente em docker-compose.yml"
    )


def test_docker_data_directory_and_gitkeep_exist() -> None:
    """Valida se o diretório docker/data existe e contém .gitkeep."""
    data_dir = Path("docker/data")
    assert data_dir.is_dir(), "Diretório docker/data não encontrado"

    gitkeep_file = data_dir / ".gitkeep"
    assert gitkeep_file.exists(), "Arquivo .gitkeep não encontrado em docker/data/"


def test_gitignore_protects_runtime_lock_files() -> None:
    """Valida se o .gitignore ignora o arquivo transitório postmaster.pid permitindo tracking do banco."""
    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists(), ".gitignore não encontrado"
    content = gitignore_path.read_text(encoding="utf-8")

    assert "docker/data/postmaster.pid" in content, (
        "docker/data/postmaster.pid não encontrado no .gitignore"
    )
    assert "docker/data/*" not in content, (
        "docker/data/* não deve estar no .gitignore para permitir versionamento do banco"
    )

