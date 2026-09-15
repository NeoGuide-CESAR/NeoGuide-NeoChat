# Tasks: Pipeline de Embeddings Vetoriais e Indexação HNSW no pgvector

## Checklist de Implementação

- [x] 1. Especificações e Planejamento SDD
  - [x] 1.1 Criar proposta da change em `openspec/changes/2026-09-15-pipeline-embeddings-indexacao-pgvector/proposal.md`
  - [x] 1.2 Criar delta spec em `openspec/changes/2026-09-15-pipeline-embeddings-indexacao-pgvector/specs/document-ingestion/spec.md`
  - [x] 1.3 Criar documento de design em `openspec/changes/2026-09-15-pipeline-embeddings-indexacao-pgvector/design.md`
  - [x] 1.4 Estruturar tarefas em `openspec/changes/2026-09-15-pipeline-embeddings-indexacao-pgvector/tasks.md`

- [x] 2. Testes Unitários Red (TDD)
  - [x] 2.1 Criar `tests/unit/test_ingestion_pipeline.py` com testes para `NormativeVectorStore` (upsert, idempotência, busca similar, threshold, filtro por norma)
  - [x] 2.2 Adicionar testes para loteamento de embeddings com rate limiting e retries com backoff exponencial
  - [x] 2.3 Adicionar testes para a função orquestradora `ingest_normative_file` com provedor fake
  - [x] 2.4 Adicionar testes para o ponto de entrada CLI `lumi.ingestion.pipeline`
  - [x] 2.5 Executar `pytest` e confirmar falhas esperadas (Red)

- [x] 3. Camada de Repositório Vetorial (Green)
  - [x] 3.1 Implementar `src/lumi/db/vector_store.py` com classe `NormativeVectorStore`
  - [x] 3.2 Implementar método atômico e idempotente `upsert_document_with_chunks`
  - [x] 3.3 Implementar método de recuperação vetorial `search_similar` com operador `<=>` do pgvector
  - [x] 3.4 Exportar `NormativeVectorStore` em `src/lumi/db/__init__.py`

- [x] 4. Pipeline de Ingestão e CLI (Green)
  - [x] 4.1 Criar modelo Pydantic `IngestionResult` em `src/lumi/ingestion/pipeline.py`
  - [x] 4.2 Implementar função de geração de embeddings em lote com backoff exponencial e rate limiting
  - [x] 4.3 Implementar função orquestradora `ingest_normative_file`
  - [x] 4.4 Implementar CLI executável com `argparse` em `src/lumi/ingestion/pipeline.py`
  - [x] 4.5 Exportar `ingest_normative_file` e `IngestionResult` em `src/lumi/ingestion/__init__.py`

- [x] 5. Qualidade de Código e Verificação Completa (Refactor)
  - [x] 5.1 Executar `uv run pytest tests/unit/test_ingestion_pipeline.py` garantindo 100% de sucesso
  - [x] 5.2 Executar toda a suíte de testes do projeto (`uv run pytest`)
  - [x] 5.3 Executar `uv run ruff check .` e `uv run ruff format --check .`
  - [x] 5.4 Executar `uv run mypy src/` garantindo ausência total de inconsistências de tipos

- [x] 6. Sincronização e Arquivamento OpenSpec
  - [x] 6.1 Atualizar status em `tasks.md`
  - [x] 6.2 Sincronizar requisitos canônicos em `openspec/specs/document-ingestion/spec.md`
  - [x] 6.3 Mover change para `openspec/changes/archive/2026-09-15-pipeline-embeddings-indexacao-pgvector/`
  - [x] 6.4 Efetuar commit local git conforme especificado
