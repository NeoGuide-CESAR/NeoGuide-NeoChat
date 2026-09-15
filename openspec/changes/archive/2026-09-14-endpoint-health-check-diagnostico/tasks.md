# Tasks: Endpoint de Health Check e Diagnóstico de Conectividade

## 1. Especificação OpenSpec
- [x] 1.1 Criar proposta da change `openspec/changes/endpoint-health-check-diagnostico/proposal.md`.
- [x] 1.2 Criar design arquitetural `openspec/changes/endpoint-health-check-diagnostico/design.md`.
- [x] 1.3 Criar checklist de tarefas `openspec/changes/endpoint-health-check-diagnostico/tasks.md`.
- [x] 1.4 Criar delta spec `openspec/changes/endpoint-health-check-diagnostico/specs/system-diagnostics/spec.md`.

## 2. Desenvolvimento Orientado a Testes (TDD) - Fase Vermelha (RED)
- [x] 2.1 Criar `tests/unit/test_health.py` com cenários:
  - Verificação de autenticação: requisição sem `X-API-Key` ou inválida retorna 401.
  - Verificação com banco conectado e saudável (mock retornando `SELECT 1` e extversion `'0.7.0'`): retorna 200 e payload compatível.
  - Verificação com falha de conexão simulada (mock levantando exceção): retorna 503 com status unhealthy.
  - Verificação com banco conectado mas pgvector ausente: retorna 200/degraded com pgvector_installed=False.
  - Verificação de que GET `/health` na raiz continua funcionando sem autenticação.
- [x] 2.2 Executar os testes e confirmar falha inicial (Fase Vermelha).

## 3. Desenvolvimento Orientado a Testes (TDD) - Fase Verde (GREEN)
- [x] 3.1 Criar schemas `DatabaseHealthInfo` e `HealthCheckResponse` em `src/lumi/schemas/health.py` e exportar em `src/lumi/schemas/__init__.py`.
- [x] 3.2 Implementar infraestrutura de sessão assíncrona do banco em `src/lumi/db/session.py`.
- [x] 3.3 Criar pacote `src/lumi/api/v1/__init__.py` e endpoint em `src/lumi/api/v1/health.py`.
- [x] 3.4 Criar agregador `src/lumi/api/v1/router.py`.
- [x] 3.5 Registrar `api_v1_router` em `src/lumi/main.py` sob o prefixo `/api/v1`.
- [x] 3.6 Executar `uv run --extra dev pytest tests/unit/test_health.py` e validar aprovação (Fase Verde).

## 4. Refatoração, Qualidade e Não-Regressão (REFACTOR)
- [x] 4.1 Executar a suíte completa de testes (`uv run --extra dev pytest`) para garantir 100% de aprovação.
- [x] 4.2 Executar linter e formatador (`uv run ruff check .` e `uv run ruff format --check .`).
- [x] 4.3 Executar checagem estática de tipos (`uv run mypy src`).

## 5. Sincronização e Arquivamento OpenSpec
- [x] 5.1 Sincronizar delta specs com a especificação canônica em `openspec/specs/system-diagnostics/spec.md`.
- [x] 5.2 Mover a change para `openspec/changes/archive/2026-09-14-endpoint-health-check-diagnostico/`.

## 6. Commit Semântico Local
- [x] 6.1 Realizar commit git com a mensagem padronizada: `feat(FEAT-15): endpoint de health check e diagnostico de conectividade`.
