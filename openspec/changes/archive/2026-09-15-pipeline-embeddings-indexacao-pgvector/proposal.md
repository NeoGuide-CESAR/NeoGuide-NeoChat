# Proposal: Pipeline de Embeddings Vetoriais e Indexação HNSW no pgvector

## Contexto
O assistente normativo Lumi NeoGuide requer a capacidade de transformar fragmentos normativos estruturados (`NormativeChunkData`), gerados a partir do parsing e chunking de normas técnicas (ex.: Neoenergia DIS-NOR-030 e DIS-NOR-053), em vetores densos de embeddings (dimensão 768) e persistí-los de forma transacional e idempotente no PostgreSQL com extensão `pgvector`. Além disso, é necessária uma interface de busca semântica eficiente baseada em similaridade de cosseno com índice HNSW e um ponto de entrada executável (CLI) para operacionalizar a ingestão em lote de documentos técnicos.

## Justificativa
1. **Desacoplamento e Resiliência:** A geração de embeddings contra modelos remotos (ex.: Gemini) está sujeita a limites de taxa (rate limits / 429) e instabilidades temporárias de rede. Um pipeline com particionamento em lotes (batching), delays defensivos e retentativas com backoff exponencial garante resiliência e estabilidade na ingestão.
2. **Idempotência Estrita na Persistência:** Documentos normativos sofrem revisões periódicas. O repositório vetorial deve garantir que re-ingerir a mesma norma ou uma nova revisão substitua atomicamente os fragmentos prévios, impedindo resíduos, chunks órfãos ou duplicatas nas buscas semânticas.
3. **Eficiência na Recuperação Semântica:** A consulta aos chunks com base no operador de distância de cosseno `<=>` do pgvector, combinada com o índice HNSW configurado na tabela `normative_chunks`, entrega buscas por similaridade em sub-segundo com filtragem dinâmica por score mínimo (threshold) e código do documento.
4. **Operacionalidade via CLI:** Engenheiros e operadores do sistema necessitam de um comando CLI intuitivo para ingestão individual de arquivos ou varredura de diretórios inteiros (`--all`) com suporte a múltiplos provedores (`gemini` e `fake`).

## Escopo

### In-Scope
- Criação de `src/lumi/db/vector_store.py` com a classe de repositório `NormativeVectorStore(session: AsyncSession)`:
  - `upsert_document_with_chunks`: transação atômica, busca/criação de `NormativeDocument`, deleção idempotente de chunks anteriores da norma e inserção em lote de novos chunks com tensores e metadados JSONB (`metadata_`).
  - `search_similar`: busca por distância de cosseno (`<=>`), cálculo de similaridade (`1.0 - distance`), filtragem por `threshold`, filtragem opcional por `document_code`, ordenação e limitação `top_k`.
- Criação de `src/lumi/ingestion/pipeline.py`:
  - Modelo Pydantic `IngestionResult` com métricas (`document_code`, `revision`, `total_chunks`, `duration_seconds`, `status`).
  - Função assíncrona de geração de embeddings com particionamento em lotes (`batch_size=32`), retentativas exponenciais (1s, 2s, 4s) e rate limiting defensivo (0.2s entre lotes).
  - Função orquestradora `ingest_normative_file`: integração fluida entre `parse_document`, `chunk_document`, geração de embeddings e persistência via `NormativeVectorStore`.
  - Ponto de entrada CLI executável (`python -m lumi.ingestion.pipeline`) com argumentos via `argparse`.
- Atualização das exportações em `src/lumi/db/__init__.py` e `src/lumi/ingestion/__init__.py`.
- Suíte completa de testes unitários em `tests/unit/test_ingestion_pipeline.py`.

### Out-of-Scope
- Endpoints HTTP/REST de ingestão no FastAPI (serão contemplados em tasks futuras de API de administração).
- Treinamento ou fine-tuning de modelos de embeddings proprietários.
