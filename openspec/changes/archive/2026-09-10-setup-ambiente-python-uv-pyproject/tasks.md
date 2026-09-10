# Tasks: Setup do Ambiente Python com uv e pyproject.toml

## 1. Manifesto e Dependências
- [x] 1.1 Criar `pyproject.toml` com metadados do projeto, dependências principais, grupos de dev e configurações de Ruff, Mypy e Pytest.
- [x] 1.2 Criar `.env.example` com todas as variáveis essenciais de ambiente documentadas.

## 2. Estrutura do Pacote e Aplicação FastAPI
- [x] 2.1 Criar `src/lumi/__init__.py`, `src/lumi/core/__init__.py` e `src/lumi/core/config.py`.
- [x] 2.2 Criar `src/lumi/main.py` com aplicação FastAPI, metadados e rotas básicas `/` e `/health`.

## 3. Testes e Lockfile
- [x] 3.1 Criar `tests/conftest.py`, `tests/unit/__init__.py` e `tests/unit/test_smoke.py`.
- [x] 3.2 Executar `uv lock` para gerar `uv.lock`.
- [x] 3.3 Executar testes automatizados via `pytest` e checagens estáticas.
