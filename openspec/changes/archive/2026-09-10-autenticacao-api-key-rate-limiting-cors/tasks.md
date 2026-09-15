# Tasks: Autenticação por API Key, Rate-Limiting e Middleware CORS

## 1. Especificação OpenSpec
- [x] 1.1 Criar proposta da change `openspec/changes/autenticacao-api-key-rate-limiting-cors/proposal.md`.
- [x] 1.2 Criar delta spec `openspec/changes/autenticacao-api-key-rate-limiting-cors/specs/api-security/spec.md`.
- [x] 1.3 Criar design arquitetural `openspec/changes/autenticacao-api-key-rate-limiting-cors/design.md`.
- [x] 1.4 Criar checklist de tarefas `openspec/changes/autenticacao-api-key-rate-limiting-cors/tasks.md`.

## 2. Desenvolvimento Orientado a Testes (TDD) - Fase Vermelha (RED)
- [x] 2.1 Criar `tests/unit/test_api_security.py` com testes para requisição sem API Key (401 com `{"detail": "Invalid or missing API Key"}`).
- [x] 2.2 Adicionar teste para requisição com API Key inválida (401).
- [x] 2.3 Adicionar teste para requisição com API Key válida (200).
- [x] 2.4 Adicionar testes para `RateLimiter` com rajada excedendo o limite por minuto (429).
- [x] 2.5 Adicionar testes para expiração de janela / reset manual do `RateLimiter`.
- [x] 2.6 Adicionar teste de preflight CORS (OPTIONS) validando cabeçalhos `Access-Control-Allow-Origin`.
- [x] 2.7 Executar os testes e confirmar falha inicial (Fase Vermelha).

## 3. Desenvolvimento Orientado a Testes (TDD) - Fase Verde (GREEN)
- [x] 3.1 Criar módulo `src/lumi/api/__init__.py`.
- [x] 3.2 Implementar `verify_api_key`, `RateLimiter` e `api_key_and_rate_limit` em `src/lumi/api/deps.py`.
- [x] 3.3 Adicionar endpoint `/api/v1/auth/check` em `src/lumi/main.py` protegido pela dependência combinada.
- [x] 3.4 Validar e garantir configuração de `CORSMiddleware` em `src/lumi/main.py` com `settings.cors_origins`.
- [x] 3.5 Executar `pytest tests/unit/test_api_security.py` e garantir que todos passem (Fase Verde).

## 4. Refatoração, Qualidade e Suíte Completa (REFACTOR)
- [x] 4.1 Executar suíte completa de testes (`uv run pytest`) para garantir não-regressão.
- [x] 4.2 Executar linter `uv run ruff check .` e formatador.
- [x] 4.3 Executar verificação de tipos estáticos `uv run mypy src`.

## 5. Sincronização e Arquivamento OpenSpec
- [x] 5.1 Criar especificação canônica em `openspec/specs/api-security/spec.md`.
- [x] 5.2 Arquivar change movendo para `openspec/changes/archive/2026-09-10-autenticacao-api-key-rate-limiting-cors/`.

## 6. Commit Semântico Local
- [x] 6.1 Executar commit semântico local com mensagem padronizada.
