# Tasks: TECH-09 - Persistência do PostgreSQL via Bind Mount no Repositório

## 1. Test-Driven Development (TDD) - Red Phase
- [x] 1.1 Criar o teste automatizado `tests/unit/test_docker_persistence.py` validando o bind mount `./docker/data:/var/lib/postgresql/data`, existência da pasta e ausência de `lumi_pgdata`.
- [x] 1.2 Executar `uv run pytest tests/unit/test_docker_persistence.py` comprovando a falha inicial (Red).

## 2. Implementação - Green Phase
- [x] 2.1 Criar o diretório `docker/data/` e adicionar o arquivo `.gitkeep`.
- [x] 2.2 Configurar `.gitignore` para ignorar `docker/data/*` exceto `!docker/data/.gitkeep`.
- [x] 2.3 Atualizar `docker-compose.yml` com bind mount `./docker/data:/var/lib/postgresql/data` e remover o volume nomeado `lumi_pgdata`.
- [x] 2.4 Atualizar `tests/unit/test_docker_config.py` para refletir o novo modelo de persistência.
- [x] 2.5 Atualizar a documentação em `docs/08-CONFIGURACAO-E-EXECUCAO-LOCAL.md` e `README.md`.
- [x] 2.6 Executar `uv run pytest tests/unit/test_docker_persistence.py` e `uv run pytest tests/unit/test_smoke.py` comprovando 100% de aprovação (Green).

## 3. Refactor, Qualidade e Finalização
- [x] 3.1 Executar linters e checagem de tipos estáticos (`uv run ruff check .` e `uv run mypy src`).
- [x] 3.2 Executar suite completa de testes unitários (`uv run pytest tests/unit/`).
- [x] 3.3 Sincronizar as especificações (OpenSpec Sync) para `openspec/specs/docker-persistence/spec.md`.
- [x] 3.4 Arquivar a change do OpenSpec (OpenSpec Archive) em `openspec/changes/archive/2026-09-19-tech-09-persistencia-dump-volume-banco-dados/`.
- [x] 3.5 Realizar commit semântico local na worktree.
