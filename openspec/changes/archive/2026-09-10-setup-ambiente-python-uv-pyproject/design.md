# Design: Setup do Ambiente Python com uv e pyproject.toml

## Architecture & Layout
Adotamos o padrão `src-layout` (`src/lumi/`) recomendado para pacotes Python modernos. Isso impede importações acidentais do diretório de trabalho local sem instalação do pacote e assegura que os testes executem contra o pacote instalado.

### Estrutura
- `pyproject.toml`: Manifesto central (PEP 621).
  - Build backend: `hatchling`.
  - Dependencies: FastAPI, Uvicorn, LangChain, SQLAlchemy, Pydantic, structlog, pgvector, asyncpg.
  - Dev dependencies: Pytest, Ruff, Mypy, Pre-commit, HTTPX.
  - Tool configurations: `tool.ruff`, `tool.mypy`, `tool.pytest.ini_options`.
- `.env.example`: Template de variáveis de ambiente.
- `src/lumi/`:
  - `__init__.py`: Versão do pacote (`__version__ = "0.1.0"`).
  - `main.py`: Aplicação FastAPI básica com rotas `/` e `/health`.
  - `core/config.py`: Definição de `Settings` via `pydantic_settings`.
- `tests/`:
  - `conftest.py`: Fixtures de teste para FastAPI `TestClient` / `AsyncClient`.
  - `unit/test_smoke.py`: Teste de inicialização e rotas básicas.

## Tooling Configs
- **Ruff**: Target Python 3.12, line-length 100, lint rules `E`, `F`, `I`, `B`, `UP`.
- **Mypy**: Python 3.12, strict mode, ignore missing imports para libs sem stubs.
- **Pytest**: asyncio_mode = "auto", testpaths = ["tests"].
