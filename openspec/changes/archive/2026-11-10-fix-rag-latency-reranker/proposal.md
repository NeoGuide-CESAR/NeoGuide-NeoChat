# Proposal: Otimização de Latência RAG e Extração de Blocos Gemini 3+

## Context
Após a adoção da família Gemini 3+ (`gemini-3.8-flash` -> `gemini-3.7-flash` -> `gemini-3.6-flash`), identificaram-se dois problemas operacionais no pipeline RAG do Lumi NeoGuide:
1. **Latência acumulada:** As etapas auxiliares síncronas/pré-geração (`QueryRewriter` e `NormativeReranker`) reutilizavam o mesmo modelo principal com raciocínio completo, elevando o tempo total antes do primeiro token de resposta ao usuário.
2. **Falhas de parsing em blocos Gemini 3+:** Respostas do LangChain/Google GenAI retornam `response.content` como uma lista estruturada de blocos (ex.: `[{"type": "thinking", ...}, {"type": "text", "text": "[2, 0]", "extras": {"signature": "..."}}]`). A coerção ingênua com `str(response.content)` causava `JSONDecodeError` no `NormativeReranker`, corrupção no `QueryRewriter` e risco de vazamento de blocos `thinking`/`reasoning` no `ChatService`.

## Motivation & Value
- **Redução de Latência:** Adotar `gemini-3.5-flash-lite` (sem thinking por padrão) via `get_fast_llm` / `get_fast_llm_chain` para `QueryRewriter` e `NormativeReranker`, mantendo `gemini-3.8-flash` com `thinking_level="low"` exclusivamente para a geração final no `ChatService`.
- **Confiabilidade do Reranker e Chat:** Centralizar a extração segura de texto em `extract_text_content(content: Any) -> str`, descartando blocos `thinking`/`reasoning` e extraindo apenas blocos textuais válidos.
- **Compatibilidade Retroativa:** Aplicar `thinking_level` apenas em modelos da família `gemini-3*`, preservando modelos legados como `gemini-1.5-pro`.

## Scope

### In-Scope
- Novas configurações em `Settings` (`src/lumi/core/config.py`): `gemini_fast_model`, `gemini_thinking_level` e `gemini_fast_thinking_level`.
- Refatoração de `src/lumi/rag/llm_factory.py` com helpers internos parametrizados, `get_fast_llm`, `get_fast_llm_chain` e `extract_text_content`.
- Atualização de `NormativeReranker`, `QueryRewriter` e `ChatService` (`create_rag_orchestrator`, `stream_chat`, `process_chat`).
- Atualização de `.env.example`, `docs/05-ARQUITETURA.md`, `docs/08-CONFIGURACAO-E-EXECUCAO-LOCAL.md` e especificações OpenSpec.
- Novos testes unitários cobrindo extração de blocos Gemini 3+, `thinking_level` condicional e uso do modelo rápido no pipeline RAG.

### Out-of-Scope
- Alterações no modelo de embeddings (`text-embedding-004`) ou no schema do banco vetorial.
