# Design: Reranker Cross-Encoder e Reescrita Contextual de Query Multi-Turn

## Arquitetura e Decisões Técnicas

### 1. Visão Geral da Arquitetura do Fluxo RAG

```mermaid
flowchart LR
    A["Pergunta do Usuário + chat_history"] --> B["QueryRewriter"]
    B -->|Query desambiguada| C["NormativeRetriever"]
    C -->|is_contingency=True| D["Curto-Circuito (Retorno Imediato)"]
    C -->|Chunks candidatos (Top-10)| E["NormativeReranker (Listwise)"]
    E -->|Chunks refinados (Top-5)| F["RetrievalResult"]
```

### 2. Componentes e Contratos de Dados

#### 2.1. Configurações (`src/lumi/core/config.py`)
Novos campos adicionados ao modelo `Settings`:
- `reranker_enabled: bool = Field(default=True, description="Habilitar reranker cross-encoder/listwise")`
- `reranker_top_n: int = Field(default=5, description="Número de chunks preservados após reranking")`
- `query_rewriter_enabled: bool = Field(default=True, description="Habilitar reescrita contextual de queries multi-turn")`

#### 2.2. `QueryRewriter` (`src/lumi/rag/rewriter.py`)
Responsável por desambiguar perguntas e resolver referências anafóricas utilizando a conversa prévia.
```python
class QueryRewriter:
    def __init__(
        self,
        llm: BaseChatModel | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm or get_llm(settings=self.settings)

    async def rewrite(
        self,
        query: str,
        chat_history: list[BaseMessage] | None = None,
    ) -> str:
        ...
```
**Regras de Execução:**
1. **Bypass imediato:** Se `not self.settings.query_rewriter_enabled` ou `not chat_history` ou `not query.strip()`, retorna `query.strip()` sem tocar na LLM (0 chamadas, latência desprezível).
2. **Engenharia de Prompt:** Instrução objetiva que orienta o modelo a produzir uma única pergunta autônoma contextualizada com as normas técnicas pertinentes (DIS-NOR-030 / DIS-NOR-053), sem responder à pergunta e sem introduzir suposições alucinadas.
3. **Resiliência:** Qualquer exceção na invocação assíncrona da LLM é capturada com log estruturado (`structlog`), retornando imediatamente `query.strip()`.

#### 2.3. `NormativeReranker` (`src/lumi/rag/reranker.py`)
Executa a reordenação semântica listwise dos fragmentos candidatos retornados pelo retriever.
```python
class NormativeReranker:
    def __init__(
        self,
        llm: BaseChatModel | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm or get_llm(settings=self.settings)

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        ...
```
**Regras de Execução:**
1. **Bypass:** Se `not self.settings.reranker_enabled` ou `len(chunks) <= effective_top_n`, retorna `chunks[:effective_top_n]` sem chamada de LLM.
2. **Avaliação Listwise:** A LLM recebe a pergunta e uma lista numerada `[0]` a `[N-1]` contendo documento, item, página e conteúdo de cada fragmento.
3. **Contrato de Saída:** O prompt exige estritamente um array JSON de inteiros representando os índices ordenados por relevância decrescente (ex.: `[2, 0, 4, 1, 3]`).
4. **Extração e Tratamento:**
   - Suporte a blocos markdown tipo ` ```json ... ``` ` ou JSON puro.
   - Validação de que os índices pertencem ao intervalo válido `[0, len(chunks)-1]`.
   - Remoção de duplicatas preservando a ordem de ranking.
   - Complemento com fragmentos originais não ranqueados caso a lista gerada seja inferior a `top_n`.
5. **Fallback:** Em qualquer erro de rede, timeout ou parsing JSON, registra log e devolve `chunks[:effective_top_n]` preservando a ordenação do cosseno.

#### 2.4. `RagContextOrchestrator` (`src/lumi/rag/chains.py`)
Coordena a execução unificada do pipeline contextual:
```python
class RagContextOrchestrator:
    def __init__(
        self,
        retriever: NormativeRetriever,
        rewriter: QueryRewriter | None = None,
        reranker: NormativeReranker | None = None,
    ) -> None:
        self.retriever = retriever
        self.rewriter = rewriter
        self.reranker = reranker

    async def get_context(
        self,
        query: str,
        chat_history: list[BaseMessage] | None = None,
        document_code: str | None = None,
    ) -> RetrievalResult:
        ...
```
**Regras de Execução:**
1. Se `rewriter` estiver presente, invoca `rewriter.rewrite(query, chat_history)`.
2. Invoca `retriever.retrieve(query=effective_query, document_code=document_code)`.
3. **Curto-circuito de contingência:** Se `retrieval_result.is_contingency is True`, retorna imediatamente `retrieval_result` (evitando reranking em casos de falta de fontes ou consultas inválidas).
4. Se `reranker` estiver presente e houver chunks recuperados, invoca `reranker.rerank(effective_query, chunks)`.
5. Retorna `RetrievalResult(query=effective_query, chunks=reranked_chunks, is_contingency=False)`.

### 3. Decisões de Desempenho e Segurança (RNF-01)
- O pipeline foi desenhado para manter o tempo total de resposta < 3s:
  - Bypass de reescrita em queries de primeiro turno economiza 1 roundtrip de LLM em ~50% das interações.
  - Listwise reranking usa prompt conciso e saída estritamente em JSON de inteiros curtos, minimizando geração de tokens e latência de inferência.
  - Curto-circuito evita chamadas desnecessárias caso a similaridade esteja abaixo do threshold.
