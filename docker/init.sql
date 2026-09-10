-- =============================================================================
-- Lumi (NeoGuide) — Inicialização do Banco de Dados PostgreSQL + pgvector
-- =============================================================================

-- Habilita a extensão pgvector para suporte a tipos vetoriais e índices HNSW
CREATE EXTENSION IF NOT EXISTS vector;
