# Tasks: Retriever Vetorial com Threshold de Similaridade e Resposta de Contingência

## Checklist de Implementação

- [x] 1. Especificações e Planejamento SDD
  - [x] 1.1 Criar proposta da change em `openspec/changes/2026-09-16-retriever-threshold-similaridade-contingencia/proposal.md`
  - [x] 1.2 Criar delta spec em `openspec/changes/2026-09-16-retriever-threshold-similaridade-contingencia/specs/rag-retriever/spec.md`
  - [x] 1.3 Criar documento de design em `openspec/changes/2026-09-16-retriever-threshold-similaridade-contingencia/design.md`
  - [x] 1.4 Estruturar checklist em `openspec/changes/2026-09-16-retriever-threshold-similaridade-contingencia/tasks.md`

- [x] 2. Fase Red do TDD
  - [x] 2.1 Criar `tests/unit/test_retriever.py` com testes de instanciação de `RetrievedChunk` e método `to_source_metadata()`
  - [x] 2.2 Adicionar testes para `RetrievalResult` validando propriedades `sources` e `formatted_context`
  - [x] 2.3 Adicionar testes para `retrieve()` com resultados válidos acima do threshold (0.70)
  - [x] 2.4 Adicionar testes para contingência com resultados vazios ou abaixo do threshold (`is_contingency=True` e `CONTINGENCY_NO_SOURCES_MESSAGE`)
  - [x] 2.5 Adicionar testes para query vazia ou whitespace retornando contingência imediatamente
  - [x] 2.6 Adicionar testes para override dinâmico de `top_k`, `threshold` e filtro por `document_code`
  - [x] 2.7 Adicionar testes com `FakeEmbeddings` assíncronos
  - [x] 2.8 Executar `pytest tests/unit/test_retriever.py` e validar falha esperada (Red)

- [x] 3. Fase Green do TDD
  - [x] 3.1 Ajustar `top_k_retrieval: int = Field(default=10)` em `src/lumi/core/config.py`
  - [x] 3.2 Adicionar eager loading com `selectinload(NormativeChunk.document)` em `src/lumi/db/vector_store.py`
  - [x] 3.3 Implementar dataclass `RetrievedChunk` e `to_source_metadata()` em `src/lumi/rag/retriever.py`
  - [x] 3.4 Implementar dataclass `RetrievalResult` com propriedades `sources` e `formatted_context` em `src/lumi/rag/retriever.py`
  - [x] 3.5 Implementar classe `NormativeRetriever` com método assíncrono `retrieve()` e telemetria structlog em `src/lumi/rag/retriever.py`
  - [x] 3.6 Exportar `RetrievedChunk`, `RetrievalResult` e `NormativeRetriever` em `src/lumi/rag/__init__.py`
  - [x] 3.7 Executar `uv run pytest tests/unit/test_retriever.py` e garantir 100% de aprovação (Green)

- [x] 4. Fase Refactor & Qualidade
  - [x] 4.1 Executar `uv run ruff check src/ tests/` e corrigir advertências
  - [x] 4.2 Executar `uv run mypy src/lumi` e corrigir inconsistências de tipos
  - [x] 4.3 Executar a suíte de testes completa do projeto (`uv run pytest`)

- [x] 5. Sincronização e Arquivamento OpenSpec
  - [x] 5.1 Mesclar especificação canônica em `openspec/specs/rag-retriever/spec.md`
  - [x] 5.2 Mover pasta da change para `openspec/changes/archive/2026-09-16-retriever-threshold-similaridade-contingencia/`
  - [x] 5.3 Marcar todas as caixas de tarefas como concluídas em `tasks.md`

- [x] 6. Commit Semântico Local
  - [x] 6.1 Executar `git add .`
  - [x] 6.2 Executar `git commit -m "feat(FEAT-07): retriever vetorial com threshold de similaridade e resposta de contingencia"`
