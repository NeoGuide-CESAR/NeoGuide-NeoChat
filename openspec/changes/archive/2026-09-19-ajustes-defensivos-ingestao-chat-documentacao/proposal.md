# Proposal: Ajustes Defensivos na Ingestão, Resiliência do Chat Service e Documentação Operacional Local

## Context
Durante a execução de testes operacionais e rotinas de ingestão em larga escala com os documentos normativos da Neoenergia Pernambuco (`DIS-NOR-030` e `DIS-NOR-053`), identificou-se a necessidade de endurecimento na tolerância a falhas na comunicação com a API Google Gemini, tanto no pipeline de vetorização quanto no runtime síncrono do assistente conversacional.
Adicionalmente, para padronizar o onboarding e a homologação do ecossistema local (PostgreSQL, Docker pgvector e CLI de ingestão), estruturou-se a documentação técnica consolidada de execução local.

## Motivation & Value
1. **Resiliência contra Rate Limiting de Embeddings (RNF-06)**: Quando múltiplos chunks normativos são vetorizados em lote, a API Google Gemini pode atingir a cota por minuto (`ResourceExhausted` / HTTP 429). O tratamento com backoff exponencial dinâmico extrai o tempo de espera sugerido pelo cabeçalho de erro da API e aguarda sem abortar o processo de indexação.
2. **Prevenção de Duplicação Vetorial no Banco**: Ao processar pastas contendo arquivos normativos em formato `.md` e `.pdf`, a ingestão agora desduplica automaticamente os arquivos pelo radical (`stem`), priorizando `.md` para evitar poluição da base vetorial.
3. **Higienização do Parser de PDF**: Correção na heurística de identificação da revisão normativa (`REV`) para descartar falsos positivos gerados por OCR/leitura de layout (como `"Nº"` ou `"PÁG"`).
4. **Resiliência no Chat Service**:
   - Persistência e commit antecipado da mensagem sanitizada do usuário no banco antes de disparar o orquestrador RAG ou a geração do LLM, evitando perda de histórico em caso de erro na rede ou no modelo.
   - Tratamento defensivo de falhas de sobrecarga temporária do provedor com log estruturado `chat_service_llm_invoke_error` e propagação de `HTTP 503 Service Unavailable` em vez de erro não tratado `500`.
5. **Configuração Explícita de Dimensionalidade Vetorial**: Garantia de repasse do parâmetro `output_dimensionality` na fábrica de embeddings Gemini, sincronizando com a dimensão configurada no banco (768).
6. **Documentação Operacional Abrangente**: Criação de `docs/08-CONFIGURACAO-E-EXECUCAO-LOCAL.md` e `docs/09-RELATORIO-DE-REVISAO-TECNICA.md`.

## Scope

### In-Scope
- `src/lumi/ingestion/parser.py`:
  - Validação estrita do regex de revisão em PDF ignorando termos espúrios (`Nº`, `NO`, `N`, `PÁG`, `PAG`).
- `src/lumi/ingestion/pipeline.py`:
  - Função auxiliar `_extract_retry_delay` para cálculo do tempo de espera defensivo.
  - Rate limiting adaptativo com logs informativos em console (`[RATE LIMIT]` e `[PROGRESSO]`).
  - Suporte CLI tanto para argumento posicional quanto `--path / -p`.
  - Desduplicação de arquivos normativos com mesmo stem priorizando Markdown sobre PDF.
- `src/lumi/rag/llm_factory.py`:
  - Inclusão do argumento padrão `output_dimensionality=resolved_settings.embedding_dimension`.
- `src/lumi/services/chat_service.py`:
  - `await self.session.commit()` imediato após persistir a mensagem do usuário em `stream_chat` e `process_chat`.
  - Bloco `try/except` em `process_chat` capturando exceções do LLM e convertendo para `HTTPException(503)` com mensagem descritiva.
- Documentação e configuração:
  - `docs/08-CONFIGURACAO-E-EXECUCAO-LOCAL.md`
  - `docs/09-RELATORIO-DE-REVISAO-TECNICA.md`
  - Atualização do `README.md`, `docker-compose.yml`, `docs/06-ESTRUTURA-DE-PASTAS.md` e lockfile `uv.lock`.

### Out-of-Scope
- Alteração no schema relacional do banco de dados ou novas tabelas Alembic.
- Modificação dos contratos de API (`ChatRequest` / `ChatResponse`).
