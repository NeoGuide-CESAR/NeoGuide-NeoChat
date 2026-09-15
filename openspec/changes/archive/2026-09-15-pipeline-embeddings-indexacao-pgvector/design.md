# Design: Pipeline de Embeddings Vetoriais e Indexação HNSW no pgvector

## Arquitetura e Decisões Técnicas

### 1. Repositório Vetorial (`NormativeVectorStore`)
A camada de repositório vetorial é encapsulada na classe `NormativeVectorStore` que opera sobre uma `AsyncSession` do SQLAlchemy 2.0.

#### Upsert e Idempotência Estrita
- Localiza o documento técnico em `normative_documents` pelo campo único `code`.
- Se inexistente, instancia `NormativeDocument` com `code`, `title` e `revision`, executando `session.flush()`.
- Se existente, atualiza `title` e `revision`.
- Para garantir idempotência estrita e evitar fragmentos órfãos ou duplicados (mesmo que revisões anteriores tenham gerado números diferentes de chunks), executa a remoção atômica de todos os chunks prévios:
  ```python
  await session.execute(delete(NormativeChunk).where(NormativeChunk.document_id == doc.id))
  ```
- Cria em lote as instâncias de `NormativeChunk` associando:
  - `document_id`: identificador do documento normativo.
  - `content`: texto com cabeçalho contextual/breadcrumb.
  - `embedding`: vetor float(768).
  - `section_code`: código da seção.
  - `section_title`: título da seção.
  - `page_number`: número da página.
  - `metadata_`: metadados JSONB (`NormativeChunkData.metadata`).
- Adiciona os novos chunks (`session.add_all(chunks)`) e efetua `session.flush()`.

#### Busca Vetorial por Similaridade de Cosseno
- Utiliza a distância de cosseno nativa do `pgvector` através do operador `<=>`:
  ```python
  distance_expr = NormativeChunk.embedding.cosine_distance(query_embedding)
  similarity_expr = (1.0 - distance_expr).label("similarity")
  ```
- Aplica o filtro de limiar semântico: `similarity_expr >= threshold`.
- Aplica filtro opcional por norma (`NormativeDocument.code == document_code`) via join relacional.
- Ordena por maior similaridade (`distance_expr.asc()`) e aplica limite `top_k`.
- Retorna tuplas `list[tuple[NormativeChunk, float]]`.

### 2. Geração Resiliente de Embeddings em Lotes
- A geração de vetores de alta dimensionalidade (768 dimensões) para centenas de chunks demanda particionamento em lotes (`batch_size=32`).
- Para mitigar limites de requisições por minuto (RPM/TPM) e eventuais erros HTTP 429 da API do Gemini:
  - Backoff exponencial com até 3 tentativas (delays de 1s, 2s, 4s).
  - Pausa defensiva (`asyncio.sleep(0.2)`) entre lotes sucessivos.
- Função desacoplada `generate_embeddings_with_retry` suporta tanto o provedor configurado no sistema quanto injeção direta de mock ou provedor `"fake"` para testes ultrarrápidos e determinísticos.

### 3. Orquestrador de Ingestão (`ingest_normative_file`)
Orquestra o fluxo de dados em cinco etapas:
1. `parse_document(file_path)` -> obtém `ParsedDocument` estruturado (Markdown ou PDF).
2. `chunk_document(parsed_doc)` -> particiona em `list[NormativeChunkData]`.
3. `generate_embeddings_with_retry([c.content for c in chunks])` -> gera tensores 768d.
4. `NormativeVectorStore.upsert_document_with_chunks(...)` -> persiste no banco em transação atômica.
5. Retorna `IngestionResult(document_code, revision, total_chunks, duration_seconds, status="success")`.

### 4. CLI de Ingestão (`lumi.ingestion.pipeline`)
- Interface de linha de comando construída com `argparse`:
  - `path`: caminho do arquivo ou pasta a ser ingerida.
  - `--provider`: escolha de provedor de embeddings (`gemini` ou `fake`).
  - `--batch-size`: tamanho do lote (padrão: 32).
  - `--all`: flag para processar recursivamente todos os arquivos suportados no diretório.
- Exibe relatório de progresso e sumário com tempo total decorrido.
