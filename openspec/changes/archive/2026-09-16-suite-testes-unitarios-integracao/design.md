# Design: Arquitetura da Suíte de Testes, Isolamento e Cobertura (TECH-08)

## Visão Geral
A suíte de testes do Lumi NeoGuide é estruturada em três camadas com objetivos distintos e complementares:
1. **Unitária (`tests/unit/`)**: Focada em funções puras, pipelines de chunking, parsing, templates de prompt, validadores de guardrails, esquemas Pydantic e serviços de domínio com dependências isoladas.
2. **Integração (`tests/integration/`)**: Focada em contratos de endpoints HTTP FastAPI, persistência assíncrona desacoplada (`BackgroundTasks`), transações de banco de dados (`AsyncSession`), busca vetorial no pgvector e jornadas completas de ponta a ponta (E2E).
3. **Avaliação IA (`tests/evals/`)**: Focada em medição de fidelidade RAG, answer relevancy e context precision via golden dataset e LLM-as-a-Judge.

## Decisões Técnicas de Design

### 1. Detecção e Skip Gracioso de Banco de Dados
Para evitar falhas duras em ambientes sem o container do PostgreSQL em execução (ex.: CI leve, máquinas locais sem Docker):
- Uma verificação rápida de conectividade tenta abrir uma conexão TCP/socket com timeout de 1 segundo.
- Se a conexão falhar ou o SQLAlchemy lançar erro operacional/de conexão, a fixture dispara `pytest.skip("PostgreSQL/pgvector não disponível no ambiente")`.
- Quando o banco está presente, a fixture inicia uma conexão com transação de nível superior (`conn.begin()`) e cria uma `AsyncSession` associada. No teardown, executa `trans.rollback()`, garantindo que nenhuma alteração persista.

### 2. Fluxo Ponta a Ponta (E2E) com Suporte Híbrido
O teste E2E em `tests/integration/test_e2e_flow.py` valida o encadeamento dos subsistemas:
- Inicialização do FastAPI com `AsyncClient` e `ASGITransport`.
- Fluxo de requisições:
  1. `GET /health`: Valida status e componentes.
  2. `POST /api/v1/sessions`: Valida criação com UUID e timestamps.
  3. `POST /api/v1/chat` (stream=True): Simula stream SSE em tempo real, validando parsing dos blocos de dados (`data: {"token": ...}`), fontes (`data: {"sources": [...]}`) e término (`data: {"event": "done", ...}`).
  4. Segundo turno de chat: Valida envio de pergunta complementar (`stream=False`), preservando o histórico da sessão e atualizando o timestamp da sessão.
  5. Telemetria analítica: Valida o acionamento da persistência assíncrona em segundo plano para `normative_query_analytics`.
  6. TTL da sessão: Simula avanço temporal superior a 1 hora e valida retorno de erro HTTP 410 Gone.

### 3. Validação Vetorial com pgvector
O teste `tests/integration/test_vector_search.py`:
- Cria registros de teste para `NormativeDocument` e `NormativeChunk` com tensores ortogonais e paralelos conhecidos (dimensão 768).
- Executa `search_similar` com `query_embedding` correspondente.
- Valida o cálculo de similaridade por cosseno (`1 - cosine_distance`).
- Valida que itens abaixo de `threshold=0.70` são eliminados.
- Valida que filtro por `document_code` restringe os resultados estritamente à norma desejada.

### 4. Fechamento de Cobertura (Meta >= 95%)
- Identificação de linhas não cobertas em módulos existentes:
  - `src/lumi/db/models.py`: representações string (`__repr__`), campos de modelos.
  - `src/lumi/db/session.py`: sanitização de erros e branches de SQLite vs PostgreSQL.
  - `src/lumi/api/deps.py`: funções auxiliares e dependências injetáveis.
  - `src/lumi/services/analytics_service.py`: cenários de retry e tratamento de exceção sob erro transitório.
  - `src/lumi/ingestion/chunker.py` e `parser.py`: ramos defensivos e casos limites.
- Implementação de testes unitários focados para elevar a cobertura a >= 95% globalmente e eliminar zonas desprotegidas.
