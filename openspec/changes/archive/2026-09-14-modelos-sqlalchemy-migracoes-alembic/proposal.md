# Proposal: Modelos de Dados SQLAlchemy e Migrações Versionadas com Alembic

## Contexto
O assistente normativo Lumi NeoGuide requer uma camada de persistência relacional e vetorial robusta, escalável e assíncrona sobre PostgreSQL com extensão pgvector. O sistema manipula documentos normativos técnicos de concessionárias (ex.: Neoenergia DIS-NOR-030 e DIS-NOR-053), seus respectivos chunks textuais vetorizados para busca semântica RAG, histórico e sessões conversacionais, e métricas analíticas de latência e similaridade de consultas normativas.

## Justificativa
A adoção do SQLAlchemy 2.0 com suporte assíncrono nativo (`asyncpg`) e migrações versionadas gerenciadas pelo Alembic garante:
1. Mapeamento declarativo type-safe e desacoplado dos esquemas do banco.
2. Suporte direto à extensão vetorial `pgvector` com índices HNSW para recuperação em sub-segundo com alta acurácia.
3. Rastreabilidade e reprodutibilidade do schema em qualquer ambiente (dev, staging, prod) via migrações Alembic assíncronas.
4. Gerenciamento estrito de transações e conexões via injeção de dependência FastAPI (`get_db_session` / `get_db`) com commit/rollback determinístico.

## Escopo

### In-Scope
- Adição da dependência `alembic>=1.13.0` no `pyproject.toml`.
- Configuração do motor assíncrono `AsyncEngine`, factory `async_sessionmaker` e gerador de sessão com rollback automático em `src/lumi/db/session.py`.
- Definição dos 5 modelos declarativos em `src/lumi/db/models.py`:
  1. `NormativeDocument` (`normative_documents`)
  2. `NormativeChunk` (`normative_chunks`) com `Vector(768)` e `metadata_` mapeado para coluna `metadata` (JSONB)
  3. `ChatSession` (`chat_sessions`) com cascade para mensagens
  4. `ChatMessage` (`chat_messages`) com índice composto temporal
  5. `NormativeQueryAnalytics` (`normative_query_analytics`) para observabilidade de consultas
- Re-exportação de `get_db` em `src/lumi/api/deps.py`.
- Estrutura completa do Alembic: `alembic.ini`, `alembic/env.py` assíncrono com metadados e settings, `alembic/script.py.mako` e migration inicial `alembic/versions/0001_initial_schema.py` com extensão `vector`, 5 tabelas e índice HNSW (`vector_cosine_ops`, m=16, ef_construction=64).
- Suíte abrangente de testes unitários em `tests/unit/test_db_models.py`.

### Out-of-Scope
- Endpoints de ingestão direta de PDFs ou parsers de texto (tratados em tasks subsequentes de ingestão).
- Execução de queries vetoriais reais contra banco PostgreSQL em produção nos testes unitários (utilização de SQLite in-memory / mocks para testes unitários de sessão).
