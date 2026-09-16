# Proposal: Retriever Vetorial com Threshold de Similaridade e Resposta de Contingência

## Contexto
O assistente normativo Lumi NeoGuide orienta engenheiros e projetistas eletricistas em conformidade com as normas técnicas da Neoenergia Pernambuco (especialmente DIS-NOR-030 e DIS-NOR-053). Para responder às dúvidas com fundamentação normativa precisa e sem alucinações, o sistema necessita de uma camada de recuperação semântica vetorial (*NormativeRetriever*) capaz de consultar os fragmentos normativos armazenados no PostgreSQL com a extensão `pgvector`. 

Adicionalmente, esta camada atua como o primeiro *guardrail* de relevância (Retrieval Guardrail): caso nenhuma evidência normativa atinja o limiar mínimo de similaridade de cosseno (padrão 0.70), ou caso a pergunta seja vazia, o sistema deve acionar imediatamente uma resposta de contingência determinística (`CONTINGENCY_NO_SOURCES_MESSAGE`), economizando tokens e dispensando chamadas desnecessárias aos modelos de linguagem (LLM).

## Justificativa
1. **Prevenção de Alucinações (Grounding Rígido):** Ao impor um threshold de similaridade mínimo (0.70), evitamos que fragmentos semanticamente distantes sejam injetados no contexto da LLM, reduzindo drasticamente o risco de alucinações normativas.
2. **Eficiência de Recursos e Latência:** Consultas fora do escopo normativo ou com baixa correlação acionam a contingência no retriever, eliminando o custo e o tempo de geração na LLM.
3. **Contratos Fortes e Compatibilidade Pydantic:** Os fragmentos retornados (`RetrievedChunk`) convertem-se diretamente para o schema canônico da API `SourceMetadata`, garantindo consistência com os eventos de stream SSE e com a interface do chat.
4. **Formatação Didática de Contexto:** A propriedade calculada `formatted_context` padroniza os blocos textuais no padrão exigido pelo prompt do sistema (`[Fonte: {document_code}, Item {section_code}, Pág. {page_number}]\n{content}`).
5. **Prevenção de Erros Assíncronos no SQLAlchemy:** Chunks recuperados no `NormativeVectorStore` precisam acessar os dados de seus documentos pais (`NormativeDocument`). Sem `selectinload(NormativeChunk.document)`, o acesso assíncrono aos relacionamentos em sessões desconectadas resulta em exceções de `MissingGreenlet`.

## Escopo

### In-Scope
- Ajuste da configuração `top_k_retrieval` padrão para 10 em `src/lumi/core/config.py`.
- Aplicação de eager loading com `selectinload(NormativeChunk.document)` no método `search_similar` de `src/lumi/db/vector_store.py`.
- Criação das estruturas de dados e classe de recuperação em `src/lumi/rag/retriever.py`:
  - Dataclass `RetrievedChunk` com campos normalizados e método de conversão `to_source_metadata() -> SourceMetadata`.
  - Dataclass `RetrievalResult` com propriedades `sources: list[SourceMetadata]` e `formatted_context: str`.
  - Classe `NormativeRetriever` com método assíncrono `retrieve(query, top_k, threshold, document_code)` suportando validação de entrada, geração assíncrona de embeddings, busca no pgvector, gating de threshold e resposta de contingência.
  - Telemetria e logging estruturado com `structlog`.
- Exportação dos novos tipos em `src/lumi/rag/__init__.py`.
- Suíte completa de testes unitários orientados a TDD em `tests/unit/test_retriever.py`.

### Out-of-Scope
- Orquestração completa do chat e streaming SSE (escopo de FEAT-08).
- Re-ranking neural com modelos cross-encoder externos.
- Expansão e enriquecimento de queries com múltiplas chamadas LLM.
