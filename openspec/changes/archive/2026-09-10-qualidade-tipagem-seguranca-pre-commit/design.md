# Design: Esteira de Qualidade com Pre-commit Hooks

## Hook Pipeline Architecture

```mermaid
flowchart LR
    Dev[git commit] --> Hooks[pre-commit framework]
    Hooks --> S1[Higiene & Sintaxe: whitespace, eof, yaml, toml, json]
    Hooks --> S2[Segurança Anti-Leak: detect-secrets, detect-private-key]
    Hooks --> S3[Qualidade Python: Ruff linter & Ruff formatter]
    Hooks --> S4[Tipagem Estática: Mypy]
    S1 & S2 & S3 & S4 -->|Todos Aprovados| Commit[Commit Criado com Sucesso]
    S1 & S2 & S3 & S4 -->|Qualquer Falha| Abort[Commit Abortado]
```

### Repositórios e Configuração
- `pre-commit/pre-commit-hooks` (v4.6.0)
- `astral-sh/ruff-pre-commit` (v0.6.9)
- `pre-commit/mirrors-mypy` (v1.11.2)
- `Yelp/detect-secrets` (v1.5.0)

### Exclusões de Escopo
Arquivos pesados gerados pelo Graphify (`graphify-out/`), worktrees temporárias (`.worktrees/`), backups e lockfiles determinísticos (`uv.lock`) não devem ser processados pelo `detect-secrets` para evitar falsos positivos com hashes SHA.
