# Tasks: Ajustes Defensivos na Ingestão, Resiliência do Chat Service e Documentação Operacional Local

## 1. Especificação OpenSpec
- [x] 1.1 Criar proposta da change `openspec/changes/archive/2026-09-19-ajustes-defensivos-ingestao-chat-documentacao/proposal.md`.
- [x] 1.2 Criar delta specs para `document-ingestion`, `chat-streaming-api` e `llm-factory`.
- [x] 1.3 Criar documento de arquitetura e design `design.md`.
- [x] 1.4 Criar checklist de tarefas `tasks.md`.

## 2. Implementação e Ajustes Defensivos (Código)
- [x] 2.1 Refinar extração de revisão de PDF em `src/lumi/ingestion/parser.py` para descartar termos como `Nº` e `PÁG`.
- [x] 2.2 Implementar `_extract_retry_delay` e rate limiting dinâmico para cota do Google Gemini em `src/lumi/ingestion/pipeline.py`.
- [x] 2.3 Implementar desduplicação de arquivos normativos com mesmo stem priorizando Markdown sobre PDF na ingestão por diretório em `src/lumi/ingestion/pipeline.py`.
- [x] 2.4 Permitir suporte a caminho posicional ou flag `--path / -p` na CLI de ingestão.
- [x] 2.5 Configurar `output_dimensionality` explícito ao instanciar `GoogleGenerativeAIEmbeddings` em `src/lumi/rag/llm_factory.py`.
- [x] 2.6 Adicionar `await self.session.commit()` imediato para a mensagem do usuário no `ChatService`.
- [x] 2.7 Envolver a invocação síncrona do LLM em bloco defensivo convertendo erros em `HTTPException(503)` com log estruturado.

## 3. Documentação Operacional e Ambiente
- [x] 3.1 Elaborar `docs/08-CONFIGURACAO-E-EXECUCAO-LOCAL.md` com instruções detalhadas de setup, Docker, banco e ingestão.
- [x] 3.2 Elaborar `docs/09-RELATORIO-DE-REVISAO-TECNICA.md` consolidando a auditoria das entregas.
- [x] 3.3 Atualizar `README.md`, `docker-compose.yml` e registrar novos documentos em `docs/06-ESTRUTURA-DE-PASTAS.md`.
- [x] 3.4 Atualizar `uv.lock`.

## 4. Verificação e Qualidade
- [x] 4.1 Executar suíte completa de testes (`uv run pytest`) atestando 100% de sucesso.
- [x] 4.2 Validar conformidade de formatação e linter (`uv run ruff check .`).
- [x] 4.3 Validar tipagem estática com Mypy (`uv run mypy src/lumi`).

## 5. Sincronização e Catálogo
- [x] 5.1 Atualizar especificações canônicas em `openspec/specs/`.
- [x] 5.2 Catalogar a tarefa `TECH-10` no ecossistema `planner/`.
