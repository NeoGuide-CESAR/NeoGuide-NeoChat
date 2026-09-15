# Tasks: Implementação de Modelos SQLAlchemy e Migrações Alembic

## Checklist de Implementação

- [x] 1. Configuração de Dependências
  - [x] 1.1 Adicionar `alembic>=1.13.0` em `pyproject.toml`
  - [x] 1.2 Validar sincronização de dependências com uv

- [x] 2. Camada de Sessão e Conexão Assíncrona
  - [x] 2.1 Criar `src/lumi/db/__init__.py` exportando Base, sessão e modelos
  - [x] 2.2 Criar `src/lumi/db/session.py` com AsyncEngine configurado (pool_size=5, max_overflow=10, pool_timeout=30)
  - [x] 2.3 Implementar gerador assíncrono `get_db_session()` com rollback automático em exceção
  - [x] 2.4 Re-exportar `get_db` em `src/lumi/api/deps.py`

- [x] 3. Modelos Declarativos SQLAlchemy 2.0
  - [x] 3.1 Criar `Base = DeclarativeBase` em `src/lumi/db/models.py`
  - [x] 3.2 Definir `NormativeDocument` com id UUID, code único, title, revision, created_at e relacionamento cascade
  - [x] 3.3 Definir `NormativeChunk` com id UUID, document_id FK, content, embedding Vector(768), section_code, section_title, page_number, metadata_ (JSONB) e relacionamento document
  - [x] 3.4 Definir `ChatSession` com id UUID, created_at, updated_at e relacionamento messages cascade
  - [x] 3.5 Definir `ChatMessage` com id UUID, session_id FK, role, content, sources JSONB, created_at e índice composto temporal
  - [x] 3.6 Definir `NormativeQueryAnalytics` com id UUID, session_id FK opcional, query_text, top_document_code, top_similarity_score, latency_ms e created_at

- [x] 4. Infraestrutura de Migração Alembic
  - [x] 4.1 Criar `alembic.ini` na raiz da worktree
  - [x] 4.2 Criar `alembic/env.py` com suporte assíncrono e target_metadata ligado a `Base.metadata` e `get_settings()`
  - [x] 4.3 Criar `alembic/script.py.mako`
  - [x] 4.4 Criar migration `alembic/versions/0001_initial_schema.py` com extensão vector, 5 tabelas, FKs e índice HNSW

- [x] 5. Testes Unitários e Integração
  - [x] 5.1 Criar `tests/unit/test_db_models.py` cobrindo todas as 5 tabelas, colunas, tipos e índices
  - [x] 5.2 Testar ciclo de vida e transacionalidade de `get_db_session` e `get_db`
  - [x] 5.3 Executar suite completa de testes e garantir 100% de sucesso

- [x] 6. Finalização e Documentação
  - [x] 6.1 Sincronizar especificações em `openspec/specs/database-schema/spec.md`
  - [x] 6.2 Arquivar change em `openspec/changes/archive/2026-09-14-modelos-sqlalchemy-migracoes-alembic/`
  - [x] 6.3 Commit na branch feat/TECH-03-sprint-2026-09-14
