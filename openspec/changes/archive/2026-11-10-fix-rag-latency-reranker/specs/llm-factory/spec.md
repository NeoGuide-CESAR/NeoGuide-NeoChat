# Delta Spec: Fábrica de LLMs Rápidos, Thinking Level e Extração de Blocos Gemini 3+

## ADDED Requirements

### Requirement: Instanciação de Modelo Rápido para Etapas Auxiliares
O módulo `lumi.rag.llm_factory` DEVE fornecer `get_fast_llm(...)` e `get_fast_llm_chain(...)` utilizando `Settings.gemini_fast_model` (`gemini-3.5-flash-lite`) e `Settings.gemini_fast_thinking_level` (`None` por padrão) quando o provedor for `"gemini"`, mantendo comportamento padrão para outros provedores.

### Requirement: Aplicação Condicional de Thinking Level em Gemini 3+
`get_llm` e `get_fast_llm` DEVEM aplicar `thinking_level` apenas quando o modelo Gemini pertencer à família `gemini-3*`, quando o nível configurado não for `None` e quando `thinking_level`/`reasoning_effort` não forem explicitamente informados via `kwargs`.

### Requirement: Extração Unificada de Texto de Blocos Gemini 3+
O módulo `lumi.rag.llm_factory` DEVE fornecer `extract_text_content(content: Any) -> str` para normalizar strings, `None` e listas de blocos estruturados, ignorando blocos de raciocínio (`thinking` / `reasoning`) e concatenando exclusivamente o conteúdo textual.
