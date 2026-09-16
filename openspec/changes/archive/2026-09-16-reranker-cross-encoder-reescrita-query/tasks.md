# Tasks: Reranker Cross-Encoder e Reescrita Contextual de Query Multi-Turn

## 1. Setup e Configuração
- [x] 1.1 Atualizar configurações em `src/lumi/core/config.py` com `reranker_enabled`, `reranker_top_n` e `query_rewriter_enabled`.

## 2. Fase RED: Testes Unitários Falhando (TDD)
- [x] 2.1 Criar `tests/unit/test_rewriter.py` com cenários de bypass (1º turno / desabilitado), reescrita multi-turn com mock e fallback gracioso sob exceção.
- [x] 2.2 Criar `tests/unit/test_reranker.py` com cenários de bypass (desabilitado / poucos chunks), reranking listwise com mock de JSON de índices, fallback gracioso sob erro/JSON inválido e top_n customizado.
- [x] 2.3 Criar `tests/unit/test_rag_chains.py` com pipeline `RagContextOrchestrator`, curto-circuito defensivo em contingência e suporte a rewriter/reranker opcionais.
- [x] 2.4 Executar pytest para atestar que os novos testes falham (RED).

## 3. Fase GREEN: Implementação dos Componentes
- [x] 3.1 Implementar `QueryRewriter` em `src/lumi/rag/rewriter.py` com suporte a bypass, prompts normativos Neoenergia e fallback gracioso.
- [x] 3.2 Implementar `NormativeReranker` em `src/lumi/rag/reranker.py` com suporte a bypass, avaliação listwise via LLM e fallback gracioso para ordenação original.
- [x] 3.3 Implementar `RagContextOrchestrator` em `src/lumi/rag/chains.py` com pipeline integrado e curto-circuito de contingência.
- [x] 3.4 Exportar `QueryRewriter`, `NormativeReranker` e `RagContextOrchestrator` em `src/lumi/rag/__init__.py`.
- [x] 3.5 Executar `pytest tests/unit/test_rewriter.py tests/unit/test_reranker.py tests/unit/test_rag_chains.py` até 100% de aprovação (GREEN).

## 4. Fase REFACTOR & Qualidade de Código
- [x] 4.1 Executar checagem de linter e formatação com `ruff check src/ tests/`.
- [x] 4.2 Executar checagem estática de tipos com `mypy src/lumi`.
- [x] 4.3 Executar a suíte completa de testes com `pytest` (garantindo 100% dos testes passando).

## 5. Sincronização e Arquivamento OpenSpec
- [x] 5.1 Sincronizar especificações canônicas em `openspec/specs/rag-reranker-rewriter/spec.md`.
- [x] 5.2 Mover o diretório da change para `openspec/changes/archive/2026-09-16-reranker-cross-encoder-reescrita-query/`.
- [x] 5.3 Marcar todas as tarefas em `tasks.md` como concluídas.
