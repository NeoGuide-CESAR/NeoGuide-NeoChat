# Spec: Esquema de Banco de Dados Relacional e Vetorial (SQLAlchemy e Alembic)

## Requirements

### Requirement: Gerenciamento Assíncrono de Sessões e Conexões
O sistema DEVE fornecer um motor assíncrono SQLAlchemy configurado com parâmetros de pool da aplicação (`pool_size=5`, `max_overflow=10`, `pool_timeout=30`), além de um gerador assíncrono de sessão (`get_db_session` / `get_db`) que realize commit automático ao finalizar sem erros e rollback automático caso ocorra qualquer exceção.

#### Scenario: Aquisição e fechamento de sessão com sucesso
- **GIVEN** a dependência `get_db_session()` invocada em um contexto assíncrono
- **WHEN** a sessão executa operações sem disparar exceções
- **THEN** as alterações devem ser comitadas automaticamente e a sessão deve ser fechada.

#### Scenario: Rollback automático em caso de falha na transação
- **GIVEN** a dependência `get_db_session()` em execução
- **WHEN** uma exceção de banco de dados ou de aplicação for lançada dentro do bloco
- **THEN** a sessão deve sofrer rollback explícito, propagar a exceção e ser fechada determinística e seguramente.

---

### Requirement: Modelos Declarativos das Entidades Normativas
O sistema DEVE definir o mapeamento declarativo das tabelas `normative_documents` e `normative_chunks` para representar normas técnicas e seus trechos vetorizados.

#### Scenario: Mapeamento de NormativeDocument
- **GIVEN** uma instância de `NormativeDocument`
- **WHEN** os atributos forem inspecionados
- **THEN** a tabela deve se chamar `normative_documents`, possuir chave primária `id` (UUID), `code` com restrição de unicidade (`UNIQUE`), `title`, `revision`, `created_at` com timezone e relacionamento `chunks` com exclusão em cascata.

#### Scenario: Mapeamento de NormativeChunk com suporte a pgvector e metadados
- **GIVEN** uma instância de `NormativeChunk`
- **WHEN** as colunas forem verificadas
- **THEN** a coluna `embedding` deve ser do tipo `Vector(768)`, a coluna física de metadados deve se chamar `metadata` (JSONB) mapeada via atributo `metadata_` no Python, e possuir chave estrangeira para `normative_documents.id` com `ondelete="CASCADE"`.

---

### Requirement: Modelos Declarativos de Sessões e Mensagens do Chat
O sistema DEVE modelar a persistência de conversas técnicas nas tabelas `chat_sessions` e `chat_messages`, permitindo histórico ordenado e integridade referencial.

#### Scenario: Mapeamento de ChatSession e ChatMessage
- **GIVEN** as entidades `ChatSession` e `ChatMessage`
- **WHEN** os metadados forem validados
- **THEN** `chat_sessions` deve possuir `created_at` e `updated_at`, relacionando-se com `chat_messages` em cascata; `chat_messages` deve conter `session_id`, `role`, `content`, `sources` (JSONB) e possuir um índice B-Tree composto temporal em `(session_id, created_at)`.

---

### Requirement: Modelo Declarativo de Métricas Analíticas
O sistema DEVE fornecer o modelo `NormativeQueryAnalytics` na tabela `normative_query_analytics` para registrar métricas de telemetria e relevância de consultas.

#### Scenario: Registro analítico de consulta normativa
- **GIVEN** uma instância de `NormativeQueryAnalytics`
- **WHEN** os campos forem avaliados
- **THEN** a entidade deve registrar `id` (UUID), `session_id` (FK opcional com `ondelete="SET NULL"`), `query_text`, `top_document_code`, `top_similarity_score`, `latency_ms` e `created_at`.

---

### Requirement: Infraestrutura Versionada de Migrações Alembic
O sistema DEVE conter configuração do Alembic com script assíncrono `alembic/env.py` e migração inicial `0001_initial_schema.py` que configure a extensão `vector`, crie as 5 tabelas e o índice HNSW vetorial com função de distância cosseno.

#### Scenario: Validação da estrutura de migração e índice HNSW
- **GIVEN** o arquivo de migração `0001_initial_schema.py`
- **WHEN** as operações DDL de `upgrade()` forem analisadas
- **THEN** deve constar `CREATE EXTENSION IF NOT EXISTS vector`, DDL das 5 tabelas, suas foreign keys e o índice vetorial HNSW com `vector_cosine_ops`, `m=16` e `ef_construction=64`.
