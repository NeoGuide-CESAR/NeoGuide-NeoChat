# Proposal: Esteira de Qualidade, Tipagem e Segurança com Git Pre-commit Hooks

## Context
O Lumi (NeoGuide) manipula chaves de API sensíveis (Google Gemini, Anthropic Claude, credenciais de banco) e exige rigor de engenharia em tipagem estática e formatação PEP 8. Conforme documentado em `docs/02-REQUISITOS.md` (RNF-08) e `docs/06-ESTRUTURA-DE-PASTAS.md` (Seção 5), commits no repositório devem ser validados preventivamente por Git hooks.

## Motivation & Value
Impedir que código com falhas de formatação, erros de tipagem estática, sintaxe inválida de arquivos de configuração (YAML/TOML/JSON) ou vazamento acidental de chaves de API/segredos seja comitado localmente por desenvolvedores.

## Scope
### In-Scope
- Criar `.pre-commit-config.yaml` na raiz com repositórios e versões estáveis.
- Configurar hooks essenciais:
  - Higiene e sintaxe: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `check-json`, `check-added-large-files`.
  - Segurança anti-leak: `detect-private-key` e `detect-secrets`.
  - Qualidade de código: `ruff` (linter com autofix) e `ruff-format`.
  - Tipagem estática: `mypy` com stubs necessários.
- Configurar filtros de exclusão para arquivos gerados e lockfiles (`graphify-out/`, `.worktrees/`, `uv.lock`, `.env.example`).
- Atualizar documentação no `README.md` com comandos de ativação local (`uv run pre-commit install`) e execução manual (`uv run pre-commit run --all-files`).
- Criar testes automatizados para validar integridade e cobertura dos hooks declarados.

### Out-of-Scope
- Configuração de CI remoto (GitHub Actions / GitLab CI).
