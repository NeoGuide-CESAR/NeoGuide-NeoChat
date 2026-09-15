# Tasks: Fábrica de Provedores de LLM e Embeddings Desacoplada (Gemini e Claude)

## 1. Configuração e Especificação
- [x] 1.1 Atualizar `Settings` em `src/lumi/core/config.py` e `.env.example` com `default_llm_provider` e `default_embedding_provider`.
- [x] 1.2 Criar artefatos OpenSpec da change (`proposal.md`, `specs/llm-factory/spec.md`, `design.md`, `tasks.md`).

## 2. Test-Driven Development (TDD)
- [x] 2.1 FASE RED: Criar `tests/unit/test_llm_factory.py` com testes unitários cobrindo instanciação de Gemini, Claude/Anthropic, FakeEmbeddings, validação de dimensionalidade (768) e tratamento de erros para provedores inválidos.
- [x] 2.2 FASE GREEN: Implementar `src/lumi/rag/llm_factory.py` com `get_llm`, `get_embeddings` e `validate_embedding_dimension`.
- [x] 2.3 FASE GREEN: Implementar `src/lumi/rag/__init__.py` exportando as funções da fábrica.
- [x] 2.4 Executar `uv run pytest tests/unit/test_llm_factory.py` e garantir 100% de sucesso.
- [x] 2.5 Executar `uv run pytest` para garantir que toda a suíte de testes do repositório continue passando.

## 3. Refatoração e Qualidade
- [x] 3.1 Executar `uv run ruff check .` e corrigir formatações/lints.
- [x] 3.2 Executar `uv run mypy src` e garantir aderência estrita de tipagem.
- [x] 3.3 Atualizar checklist de tarefas marcando todos os passos como concluídos.

## 4. Sincronização e Finalização
- [x] 4.1 Consolidar especificação canônica em `openspec/specs/llm-factory/spec.md`.
- [x] 4.2 Arquivar change em `openspec/changes/archive/2026-09-10-fabrica-provedores-llm-gemini-claude/`.
- [x] 4.3 Criar commit semântico local no git.
