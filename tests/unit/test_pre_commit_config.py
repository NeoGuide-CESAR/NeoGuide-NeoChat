"""Testes de validação estática do arquivo de configuração do pre-commit."""

from pathlib import Path


def test_pre_commit_config_exists() -> None:
    """Valida se o arquivo .pre-commit-config.yaml existe na raiz."""
    config_path = Path(".pre-commit-config.yaml")
    assert config_path.exists(), ".pre-commit-config.yaml não encontrado na raiz"


def test_pre_commit_hooks_coverage() -> None:
    """Valida se os hooks essenciais de higiene, ruff, mypy e detect-secrets estão configurados."""
    config_path = Path(".pre-commit-config.yaml")
    content = config_path.read_text(encoding="utf-8")

    # Higiene
    assert "trailing-whitespace" in content
    assert "end-of-file-fixer" in content
    assert "check-yaml" in content
    assert "check-toml" in content
    assert "check-json" in content
    assert "detect-private-key" in content

    # Ruff
    assert "astral-sh/ruff-pre-commit" in content
    assert "id: ruff" in content
    assert "id: ruff-format" in content

    # Mypy
    assert "mirrors-mypy" in content
    assert "id: mypy" in content

    # Segurança anti-leak
    assert "detect-secrets" in content


def test_pre_commit_exclusions() -> None:
    """Valida se diretórios gerados e arquivos de exemplo/lock estão excluídos."""
    config_path = Path(".pre-commit-config.yaml")
    content = config_path.read_text(encoding="utf-8")

    assert "graphify-out" in content
    assert ".worktrees" in content
