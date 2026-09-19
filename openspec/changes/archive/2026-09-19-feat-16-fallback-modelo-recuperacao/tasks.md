# Tasks: Cadeia de Fallback Automático de Modelos Generativos Gemini (FEAT-16)

## 1. Setup e Especificações
- [x] 1.1 Criar proposta, design e delta spec de resiliência de modelos LLM em `openspec/changes/feat-16-fallback-modelo-recuperacao/`.

## 2. Test-Driven Development (Fase Red)
- [x] 2.1 Criar suíte de testes unitários em `tests/unit/test_llm_fallback.py` cobrindo sucesso primário, 1º fallback, 2º fallback e esgotamento 503.
- [x] 2.2 Executar testes e registrar falha inicial esperada (Red).

## 3. Implementação da Cadeia de Fallback (Fase Green)
- [x] 3.1 Atualizar configurações padrão e lista de fallback em `src/lumi/core/config.py`.
- [x] 3.2 Implementar fábrica e utilitários da cadeia de modelos em `src/lumi/rag/llm_factory.py`.
- [x] 3.3 Implementar fallback sequencial e logs estruturados em `src/lumi/services/chat_service.py` (`process_chat` e `stream_chat`).
- [x] 3.4 Implementar fallback sequencial e logs estruturados em `src/lumi/rag/rewriter.py` (`QueryRewriter.rewrite`).
- [x] 3.5 Executar testes e validar aprovação de 100% dos testes unitários (Green).

## 4. Refatoração e Qualidade (Fase Refactor)
- [x] 4.1 Executar validação de linter com `ruff check .` e corrigir apontamentos.
- [x] 4.2 Executar checagem estática de tipos com `mypy src` e corrigir divergências.
- [x] 4.3 Executar smoke tests para assegurar não regressão.

## 5. Finalização OpenSpec e Git
- [x] 5.1 Sincronizar especificações para `openspec/specs/llm-resilience/spec.md`.
- [x] 5.2 Arquivar change em `openspec/changes/archive/2026-09-19-feat-16-fallback-modelo-recuperacao/`.
- [x] 5.3 Realizar commit semântico local na branch da worktree.
