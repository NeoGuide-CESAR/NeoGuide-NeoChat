# Tasks: Otimização de Latência RAG e Extração de Blocos Gemini 3+

## 1. Configuração e Fábrica de LLMs
- [x] 1.1 Adicionar `gemini_fast_model`, `gemini_thinking_level` e `gemini_fast_thinking_level` em `src/lumi/core/config.py`.
- [x] 1.2 Implementar `extract_text_content`, `get_fast_llm`, `get_fast_llm_chain` e aplicação condicional de `thinking_level` para Gemini 3+ em `src/lumi/rag/llm_factory.py`.
- [x] 1.3 Exportar novos símbolos em `llm_factory.py` e `src/lumi/rag/__init__.py`.

## 2. Pipeline RAG e ChatService
- [x] 2.1 Atualizar `NormativeReranker` (`src/lumi/rag/reranker.py`) para usar `get_fast_llm` por padrão e `extract_text_content` em `rerank()`.
- [x] 2.2 Atualizar `QueryRewriter` (`src/lumi/rag/rewriter.py`) para usar `get_fast_llm_chain` por padrão e `extract_text_content` em `rewrite()`.
- [x] 2.3 Atualizar `create_rag_orchestrator`, `ChatService.rag_orchestrator`, `stream_chat` e `process_chat` em `src/lumi/services/chat_service.py`.

## 3. Testes, Qualidade e Documentação
- [x] 3.1 Adicionar testes unitários em `test_llm_factory.py`, `test_reranker.py`, `test_rewriter.py` e `test_chat_service.py`.
- [x] 3.2 Validar suíte `pytest tests/unit`, `ruff check`, `ruff format` e `mypy src`.
- [x] 3.3 Atualizar `.env.example`, `docs/05-ARQUITETURA.md`, `docs/08-CONFIGURACAO-E-EXECUCAO-LOCAL.md` e sincronizar specs OpenSpec.
