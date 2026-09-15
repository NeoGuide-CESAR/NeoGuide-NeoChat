# Tasks: Guardrails de Entrada contra Prompt Injection e Sanitização de PII

## 1. Fase RED (Testes Unitários)
- [x] 1.1 Criar `tests/unit/test_guardrails.py` com testes unitários cobrindo detecção de prompt injection e jailbreak.
- [x] 1.2 Adicionar testes para sanitização de PII (CPF formatado e desformatado, CNPJ formatado e desformatado, conta contrato / faturamento).
- [x] 1.3 Adicionar testes para verificação de escopo temático (elétrico/normativo permitido vs receitas/futebol/horóscopo recusados).
- [x] 1.4 Adicionar testes para a função orquestradora `validate_input(text)` e estrutura `GuardrailResult`.
- [x] 1.5 Executar `uv run pytest tests/unit/test_guardrails.py` e constatar falha inicial (FASE RED).

## 2. Fase GREEN (Implementação)
- [x] 2.1 Criar `src/lumi/rag/__init__.py` exportando os componentes principais.
- [x] 2.2 Implementar a estrutura `GuardrailResult` em `src/lumi/rag/guardrails.py`.
- [x] 2.3 Implementar funções de detecção de injeção (`detect_prompt_injection`) e sanitização de PII (`sanitize_pii`).
- [x] 2.4 Implementar a verificação de escopo temático (`check_domain_scope`) e mensagem cortês de recusa.
- [x] 2.5 Implementar o orquestrador `validate_input(text: str) -> GuardrailResult`.
- [x] 2.6 Executar `uv run pytest tests/unit/test_guardrails.py` e constatar sucesso (FASE GREEN).

## 3. Fase REFACTOR & Qualidade
- [x] 3.1 Otimizar regexes compiladas em nível de módulo (`re.compile`) com tratamento insensível a maiúsculas e acentos.
- [x] 3.2 Executar suíte completa de testes automatizados (`uv run pytest`).
- [x] 3.3 Executar linter e formatação (`uv run ruff check .` e `uv run ruff format --check .`).
- [x] 3.4 Executar checagem estática de tipos (`uv run mypy src`).

## 4. Sincronização e Arquivamento OpenSpec
- [x] 4.1 Sincronizar especificações criando `openspec/specs/input-guardrails/spec.md`.
- [x] 4.2 Arquivar a change movendo o diretório para `openspec/changes/archive/2026-09-10-guardrails-entrada-injection-pii/`.
