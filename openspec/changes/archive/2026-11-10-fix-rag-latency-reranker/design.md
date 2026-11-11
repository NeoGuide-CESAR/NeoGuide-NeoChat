# Design: Arquitetura Dual de Modelos Gemini e Extração de Blocos Gemini 3+

## Architecture Overview
O fluxo RAG passa a separar explicitamente o perfil de inferência auxiliar do perfil de geração final:
- **Etapas Auxiliares (`QueryRewriter` e `NormativeReranker`):** Utilizam `gemini-3.5-flash-lite` sem `thinking_level` por padrão (`gemini_fast_thinking_level=None`), priorizando baixa latência. No `QueryRewriter`, a cadeia de fallback rápido (`get_fast_llm_chain`) ordena `[gemini_fast_model, gemini_model, *gemini_fallback_models]` até o teto de `MAX_FALLBACK_ATTEMPTS (3)`.
- **Geração Final (`ChatService`):** Utiliza `gemini-3.8-flash` com `thinking_level="low"` (aplicado apenas a modelos `gemini-3*` quando não sobrescrito por kwargs).
- **Extração de Conteúdo (`extract_text_content`):** Normaliza strings, `None` e listas heterogêneas de blocos do Gemini 3+, ignorando `type in ("thinking", "reasoning")` e concatenando apenas texto útil.

## Component Breakdown
1. `src/lumi/core/config.py`: `gemini_fast_model`, `gemini_thinking_level`, `gemini_fast_thinking_level`.
2. `src/lumi/rag/llm_factory.py`: `_build_llm`, `_build_llm_chain`, `get_fast_llm`, `get_fast_llm_chain`, `extract_text_content`.
3. `src/lumi/rag/reranker.py`: `NormativeReranker.__init__` usando `get_fast_llm` quando `llm` não é injetado, e `rerank()` usando `extract_text_content`.
4. `src/lumi/rag/rewriter.py`: `QueryRewriter.models` usando `get_fast_llm_chain` quando `_llm` não é injetado, e `rewrite()` usando `extract_text_content`.
5. `src/lumi/services/chat_service.py`: `create_rag_orchestrator` com suporte a `fast_llm` opcional e padrão rápido, e `stream_chat`/`process_chat` utilizando `extract_text_content`.
