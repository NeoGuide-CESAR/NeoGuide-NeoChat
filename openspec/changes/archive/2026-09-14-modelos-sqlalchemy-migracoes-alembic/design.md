# Design: Modelos de Dados SQLAlchemy e Migrações Versionadas com Alembic

## Arquitetura e Decisões Técnicas

### 1. Camada de Persistência Assíncrona (SQLAlchemy 2.0 + asyncpg)
- Utilização de `create_async_engine` conectado via URL do PostgreSQL assíncrono (`postgresql+asyncpg://...`).
- Dimensionamento do Pool de conexões orientado por `Settings`:
  - `pool_size = 5`
  - `max_overflow = 10`
  - `pool_timeout = 30`
- Gerenciamento de ciclo de vida com `async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)` e context manager `get_db_session()`:
  - Inicializa sessão assíncrona.
  - Executa `yield session`.
  - Executa `commit()` automático em caso de sucesso.
  - Executa `rollback()` e re-lança exceções em caso de falha.
  - Garante fechamento determinístico via bloco `finally: await session.close()`.

### 2. Modelagem Relacional e Vetorial
```
+-----------------------------------+        +-----------------------------------+
| normative_documents               |        | normative_chunks                  |
+-----------------------------------+        +-----------------------------------+
| id: UUID (PK)                     | 1    N | id: UUID (PK)                     |
| code: VARCHAR(50) (UNIQUE)        |<-------| document_id: UUID (FK, CASCADE)  |
| title: VARCHAR(255)               |        | content: TEXT                     |
| revision: VARCHAR(20)             |        | embedding: Vector(768)            |
| created_at: TIMESTAMPTZ           |        | section_code: VARCHAR(50)         |
+-----------------------------------+        | section_title: VARCHAR(255)       |
                                             | page_number: INTEGER              |
                                             | metadata: JSONB                   |
                                             +-----------------------------------+

+-----------------------------------+        +-----------------------------------+
| chat_sessions                     |        | chat_messages                     |
+-----------------------------------+        +-----------------------------------+
| id: UUID (PK)                     | 1    N | id: UUID (PK)                     |
| created_at: TIMESTAMPTZ           |<-------| session_id: UUID (FK, CASCADE)   |
| updated_at: TIMESTAMPTZ           |        | role: VARCHAR(20)                 |
+-----------------------------------+        | content: TEXT                     |
                                             | sources: JSONB                    |
                                             | created_at: TIMESTAMPTZ           |
                                             +-----------------------------------+

+-----------------------------------+
| normative_query_analytics         |
+-----------------------------------+
| id: UUID (PK)                     |
| session_id: UUID (FK, SET NULL)   |
| query_text: TEXT                  |
| top_document_code: VARCHAR(50)    |
| top_similarity_score: FLOAT       |
| latency_ms: INTEGER               |
| created_at: TIMESTAMPTZ           |
+-----------------------------------+
```

### 3. Detalhes de Modelagem
- **Nomeação de Atributo de Metadados:** Para evitar colisão com o atributo interno do SQLAlchemy (`Base.metadata`), o atributo de modelo na entidade `NormativeChunk` é nomeado `metadata_ = mapped_column("metadata", JSONB, ...)` apontando para o nome físico `"metadata"`.
- **Índice HNSW para Recuperação Vetorial:** Criação de índice vetorial na coluna `normative_chunks.embedding` com métrica de cosseno (`vector_cosine_ops`), `m=16` e `ef_construction=64` para busca por vizinhos mais próximos de altíssimo desempenho.
- **Índice Temporal Composto:** Criação de índice B-Tree composto em `chat_messages(session_id, created_at)` para otimizar a recuperação sequencial e paginada do histórico conversacional.

### 4. Migrações com Alembic Assíncrono
- `alembic.ini` configurado para carregar scripts da pasta `alembic/`.
- `alembic/env.py` adaptado para rodar assincronamente (`run_migrations_online` executando `connect()` assíncrono ou adaptador com `asyncpg`), compartilhando a configuração de `get_settings().database_url` e `Base.metadata`.
- `0001_initial_schema.py`:
  - Ativação prévia da extensão `vector`: `CREATE EXTENSION IF NOT EXISTS vector`.
  - Criação das tabelas `normative_documents`, `normative_chunks`, `chat_sessions`, `chat_messages` e `normative_query_analytics`.
  - Criação do índice HNSW usando comandos DDL compatíveis com PostgreSQL / pgvector.
