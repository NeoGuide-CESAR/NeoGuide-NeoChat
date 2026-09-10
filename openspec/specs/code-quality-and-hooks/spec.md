# Spec: Qualidade de Código e Git Pre-commit Hooks

## Requirements

### Requirement: Configuração Declarativa de Hooks
O projeto DEVE possuir um arquivo `.pre-commit-config.yaml` válido na raiz contendo hooks para higiene de arquivos, validação de sintaxe, formatação e verificação estática.

#### Scenario: Validação de Sintaxe de Configuração
- **GIVEN** arquivos YAML, TOML e JSON no repositório
- **WHEN** os hooks `check-yaml`, `check-toml` e `check-json` forem executados
- **THEN** erros de parse de sintaxe devem ser reportados impedindo o commit.

### Requirement: Prevenção de Vazamento de Segredos
A esteira DEVE integrar `detect-secrets` e `detect-private-key` para bloquear commits com padrões de credenciais e chaves criptográficas privadas.

#### Scenario: Detecção Preventiva
- **GIVEN** tentativas de commit de arquivos com chaves privadas ou senhas
- **WHEN** o hook `detect-secrets` ou `detect-private-key` for disparado
- **THEN** o commit deve ser abortado indicando a linha com suspeita de segredo.

### Requirement: Linter e Formatação com Ruff
A esteira DEVE executar `ruff` e `ruff-format` para manter a base de código alinhada ao PEP 8 e normas do projeto.

#### Scenario: Autoformatação e Correção de Imports
- **GIVEN** arquivos Python modificados
- **WHEN** o hook do Ruff for executado
- **THEN** imports não utilizados devem ser limpos e quebras de linha/aspas padronizadas automaticamente.
