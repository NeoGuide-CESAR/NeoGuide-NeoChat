# Proposal: Reranker Cross-Encoder e Reescrita Contextual de Query Multi-Turn

## Contexto
O assistente normativo Lumi NeoGuide atua no esclarecimento de dúvidas técnicas sobre normas de distribuição e atendimento elétrico da Neoenergia Pernambuco (DIS-NOR-030 e DIS-NOR-053). Em conversas multi-turn, as perguntas dos projetistas frequentemente contêm referências pronominais e elipses contextuais (ex.: "E se for acima de 40 apartamentos?", "Qual tabela se aplica a ela?", "Onde fica essa exigência?"). Quando essas perguntas são enviadas diretamente para a busca vetorial densa, a qualidade da recuperação cai significativamente pela ausência dos termos normativos explícitos introduzidos em turnos anteriores.

Além disso, a recuperação densa baseada exclusivamente em similaridade de cosseno (bi-encoder) pode priorizar fragmentos com termos sobrepostos mas menor densidade de relevância normativa estrita. A reordenação semântica listwise dos fragmentos candidatos (top-10 para top-5) assegura que apenas as evidências mais pertinentes e acionáveis componham o contexto final entregue à síntese da LLM, mantendo o tempo de resposta estritamente dentro do teto de 3 segundos (RNF-01).

## Justificativa
1. **Desambiguação Contextual Multi-Turn (QueryRewriter):** Reformulação autônoma de perguntas elípticas ou com pronomes anafóricos utilizando o histórico recente da conversa, direcionando a busca vetorial para os termos normativos corretos sem inventar regras.
2. **Otimização de Latência e Recursos:** Bypass imediato da chamada de LLM no primeiro turno (`chat_history` vazio/nulo) ou quando a reescrita estiver desabilitada via configuração (`query_rewriter_enabled=False`).
3. **Reordenação Semântica de Alta Precisão (NormativeReranker):** Estratégia listwise avaliando os fragmentos candidatos com prompt estruturado de baixo custo que retorna um array JSON com os índices dos fragmentos mais relevantes, selecionando o `top_n` (padrão 5).
4. **Resiliência e Tolerância a Falhas (Fallback Gracioso):** Qualquer falha de rede, timeout da LLM ou erro de parsing de JSON reverte automaticamente e transparentemente para a query original ou para a ordenação original dos chunks por cosseno.
5. **Orquestração Defensiva e Curto-Circuito (RagContextOrchestrator):** Pipeline unificado `chat_history` ➔ `QueryRewriter` ➔ `NormativeRetriever` ➔ `NormativeReranker` ➔ `RetrievalResult`, com interrupção imediata caso o retriever dispare contingência determinística (`is_contingency=True`), evitando desperdício de chamadas de LLM.

## Escopo

### In-Scope
- Atualização de `src/lumi/core/config.py`:
  - `reranker_enabled: bool = True`
  - `reranker_top_n: int = 5`
  - `query_rewriter_enabled: bool = True`
- Implementação de `QueryRewriter` em `src/lumi/rag/rewriter.py`:
  - Bypass imediato no 1º turno ou quando desabilitado.
  - Reescrita contextual multi-turn focada em normas Neoenergia.
  - Fallback gracioso para a query original em caso de erro da LLM.
- Implementação de `NormativeReranker` em `src/lumi/rag/reranker.py`:
  - Bypass quando desabilitado ou `len(chunks) <= top_n`.
  - Avaliação listwise via LLM gerando array JSON de índices.
  - Fallback gracioso para a lista original de chunks sob qualquer falha.
- Implementação de `RagContextOrchestrator` em `src/lumi/rag/chains.py`:
  - Fluxo orquestrado histórico -> rewriter -> retriever -> reranker -> RetrievalResult.
  - Curto-circuito defensivo em contingência do retriever.
- Exportação dos novos módulos em `src/lumi/rag/__init__.py`.
- Testes unitários abrangentes em `tests/unit/test_rewriter.py`, `tests/unit/test_reranker.py` e `tests/unit/test_rag_chains.py`.

### Out-of-Scope
- Camada de geração final de streaming SSE da API (escopo de FEAT-09).
- Fine-tuning ou hospedagem local de modelos de cross-encoder pesados via HuggingFace (privilegia-se listwise leve via LLM ágil ou bypass configurável).
