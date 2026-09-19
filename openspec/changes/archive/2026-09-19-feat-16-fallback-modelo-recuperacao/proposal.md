# Proposal: Cadeia de Fallback Automático de Modelos Generativos Gemini (FEAT-16)

## Context
O Lumi NeoGuide atua como assistente normativo inteligente para infraestrutura de distribuição e telecomunicações da Neoenergia Pernambuco, orquestrando consultas complexas com busca vetorial RAG e geração de respostas através de modelos Google Gemini. Em ambientes de produção de alta demanda, modelos generativos de ponta estão sujeitos a indisponibilidades transitórias, sobrecargas de infraestrutura e erros de cota (HTTP 503 Service Unavailable, HTTP 429 Too Many Requests). Atualmente, qualquer falha durante a invocação da LLM interrompe o fluxo de atendimento ao usuário.

## Motivation & Value
A introdução de uma cadeia de resiliência e fallback automático sequencial entre modelos Google Gemini (`gemini-3.8-flash` -> `gemini-3.7-flash` -> `gemini-3.6-flash`) assegura alta disponibilidade (HA) e recuperação transparente sem intervenção do usuário ou do operador.
Benefícios centrais:
1. **Resiliência e Tolerância a Falhas:** Redução drástica da taxa de erro 503 em requisições de usuários quando o modelo primário estiver sobrecarregado.
2. **Degradação Graciosa:** Utilização progressiva de versões estáveis do Gemini Flash com limite estrito de até 3 tentativas sequenciais.
3. **Observabilidade Estruturada:** Emissão de telemetria rica via `structlog` (`llm_fallback_attempt`) registrando o modelo com falha, o próximo modelo da cadeia, a tentativa e o erro ocorrido.
4. **Proteção de Recursos:** Esgotamento seguro após 3 tentativas com lançamento explícito de `HTTPException(status_code=503)` informando a sobrecarga temporária.

## Scope

### In-Scope
- Atualização do modelo padrão no `Settings` (`src/lumi/core/config.py`) para `gemini-3.8-flash` e inclusão da lista de fallback `["gemini-3.7-flash", "gemini-3.6-flash"]`.
- Extensão de `src/lumi/rag/llm_factory.py` com funções e constantes de suporte: `DEFAULT_GEMINI_PRIMARY_MODEL`, `DEFAULT_GEMINI_FALLBACK_MODELS`, `MAX_FALLBACK_ATTEMPTS`, `get_llm_chain` e `get_model_name`.
- Implementação da execução resiliente com até 3 tentativas em `src/lumi/services/chat_service.py` para modo síncrono (`process_chat`) e streaming SSE (`stream_chat`).
- Implementação do fallback automático na reescrita de consultas em `src/lumi/rag/rewriter.py` (`QueryRewriter.rewrite`).
- Registro estruturado com `logger.warning("llm_fallback_attempt", failed_model=..., next_model=..., attempt=..., error=...)`.
- Lançamento de `HTTPException(status_code=503, detail=...)` após esgotamento de todas as 3 tentativas.
- Criação de testes unitários isolados em `tests/unit/test_llm_fallback.py` cobrindo cenários com sucesso primário, recuperação no 1º fallback, recuperação no 2º fallback e esgotamento com erro 503.

### Out-of-Scope
- Chaveamento dinâmico entre provedores de IA distintos (ex.: fallback do Gemini para Anthropic Claude).
- Fallback em geradores de embeddings (mantido em `gemini_embedding_model`).
