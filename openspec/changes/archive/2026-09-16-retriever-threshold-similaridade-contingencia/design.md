# Design: Retriever Vetorial com Threshold de Similaridade e Resposta de Contingência

## Arquitetura e Decisões Técnicas

### 1. Modelos de Dados em `src/lumi/rag/retriever.py`

#### `RetrievedChunk` (Dataclass)
Representa um fragmento normativo recuperado do banco vetorial já desacoplado da sessão SQLAlchemy:
```python
@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_code: str
    document_title: str
    revision: str
    section_code: str | None
    section_title: str | None
    page_number: int | None
    content: str
    similarity_score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_source_metadata(self) -> SourceMetadata:
        """Converte o fragmento recuperado para o contrato SourceMetadata da API."""
        section = self.section_code or self.section_title or "Geral"
        page = self.page_number if (self.page_number is not None and self.page_number >= 1) else 1
        # Garante score no intervalo [0.0, 1.0]
        score = max(0.0, min(1.0, float(self.similarity_score)))
        return SourceMetadata(
            document_code=self.document_code,
            revision=self.revision or "",
            section=section,
            page=page,
            relevance_score=score,
            snippet=self.content,
        )
```

#### `RetrievalResult` (Dataclass)
Representa o resultado consolidado da recuperação semântica, contendo as propriedades calculadas para o consumo pelo pipeline RAG:
```python
@dataclass
class RetrievalResult:
    query: str
    chunks: list[RetrievedChunk]
    is_contingency: bool
    contingency_message: str | None = None

    @property
    def sources(self) -> list[SourceMetadata]:
        """Gera a lista de SourceMetadata para inclusão na resposta estruturada e eventos SSE."""
        if self.is_contingency or not self.chunks:
            return []
        return [c.to_source_metadata() for c in self.chunks]

    @property
    def formatted_context(self) -> str:
        """Formata os fragmentos para injeção no prompt mestre RAG."""
        if self.is_contingency or not self.chunks:
            return ""

        formatted_pieces: list[str] = []
        for c in self.chunks:
            sec = c.section_code or "Geral"
            pag = c.page_number if c.page_number is not None else "N/A"
            header = f"[Fonte: {c.document_code}, Item {sec}, Pág. {pag}]"
            formatted_pieces.append(f"{header}\n{c.content}")

        return "\n\n".join(formatted_pieces)
```

### 2. Classe `NormativeRetriever`

#### Inicialização Flexível
```python
class NormativeRetriever:
    def __init__(
        self,
        session: AsyncSession | None = None,
        vector_store: NormativeVectorStore | None = None,
        embeddings: Embeddings | None = None,
        settings: Settings | None = None,
    ) -> None:
```
- Injeta ou resolve dependências automaticamente via `get_settings()` e `get_embeddings()`.
- Cria `NormativeVectorStore(session)` se `session` for fornecida e `vector_store` for omitido.

#### Fluxo de Execução de `retrieve()`
```
[Query de Entrada]
       │
       ▼
 [Sanitização] ──(query vazia ou whitespace?)──► Retorna Contingência Imediata (is_contingency=True)
       │ Não
       ▼
[Embeddings Assíncronos]
 (aembed_query / fallback)
       │
       ▼
[Busca Vetorial pgvector]
 (search_similar com selectinload)
       │
       ▼
[Gating de Threshold] ──(Nenhum chunk >= threshold?)──► Retorna Contingência (is_contingency=True)
       │ Sim
       ▼
[Retorno Bem-Sucedido] (is_contingency=False, chunks tipados)
```

### 3. Eager Loading em `NormativeVectorStore`
Em `src/lumi/db/vector_store.py`:
- Adicionar `from sqlalchemy.orm import selectinload`.
- No método `search_similar`:
```python
stmt = select(NormativeChunk, similarity_expr).options(
    selectinload(NormativeChunk.document)
)
```
Garante que o carregamento do objeto pai `NormativeDocument` ocorra na mesma transação/query assíncrona, eliminando riscos de `sqlalchemy.orm.exc.DetachedInstanceError` ou `MissingGreenlet`.

### 4. Telemetria com `structlog`
A cada recuperação, eventos estruturados são emitidos:
- `retriever_query_started`: query, top_k, threshold, document_code.
- `retriever_contingency_triggered`: razão (empty_query ou no_chunks_above_threshold).
- `retriever_query_success`: chunks_found, top_score, lowest_score.

### 5. Configuração do Sistema (`src/lumi/core/config.py`)
- `top_k_retrieval`: alterado o valor default de `5` para `10`.
