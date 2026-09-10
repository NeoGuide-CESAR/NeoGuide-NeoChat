# Proposal: Schemas Pydantic para Validação de Contratos da API (Chat e Sessão)

## Context
O assistente normativo Lumi (NeoGuide) atende projetistas de infraestrutura de telecomunicações e instalações elétricas por meio de uma interface conversacional integrada ao Wizard NeoGuide. Para assegurar confiabilidade, integridade de dados e conformidade com a arquitetura descrita em `docs/05-ARQUITETURA.md` (Seção 3) e `docs/06-ESTRUTURA-DE-PASTAS.md`, a API FastAPI exige contratos estritos de entrada e saída (DTOs) com validação orientada a Pydantic v2.

## Motivation & Value
A ausência de schemas formais de validação expõe os endpoints a dados corrompidos, tipos inadequados e falhas silenciosas durante o parsing de mensagens e streaming de eventos SSE. A adoção de modelos Pydantic v2 fornece:
- Validação determinística em tempo de execução para parâmetros de consulta, UUIDs, paginação e scores de similaridade.
- Tipagem estática forte garantindo interoperabilidade entre o frontend e a esteira de orquestração RAG (LangChain).
- Documentação OpenAPI/Swagger gerada automaticamente para os contratos de Chat e Sessão.
- Proteção contra injeção de mensagens em branco ou papéis (roles) desconhecidos no histórico multi-turn.

## Scope

### In-Scope
- Criação de `src/lumi/schemas/chat.py`:
  - `SourceMetadata`: metadados de normas consultadas (`document_code`, `revision`, `section`, `page`, `relevance_score`, `snippet`).
  - `ChatRequest`: contrato de entrada de perguntas (`session_id`, `message`, `stream`).
  - `ChatResponse`: contrato de resposta síncrona com fontes (`session_id`, `response`, `sources`, `created_at`).
  - Schemas de eventos Server-Sent Events (SSE): `StreamTokenEvent`, `StreamSourcesEvent`, `StreamDoneEvent`, `StreamErrorEvent`.
- Criação de `src/lumi/schemas/session.py`:
  - `SessionCreateResponse`: resposta de inicialização de sessão.
  - `ChatMessageResponse`: mensagem individual no histórico com papéis (`user`, `assistant`, `system`).
  - `SessionDetailResponse`: detalhamento de sessão contendo metadados e histórico ordenado de mensagens.
- Criação de `src/lumi/schemas/__init__.py` exportando os modelos.
- Validações específicas de regras de negócio:
  - Rejeição de mensagens vazias ou compostas unicamente por espaços em branco.
  - Validação estrita de UUIDs para identificadores de sessão.
  - `page >= 1` e `0.0 <= relevance_score <= 1.0`.
  - Restrição de papéis (`role`) aos literais autorizados.
- Suíte completa de testes unitários em `tests/unit/test_schemas.py` cobrindo casos de sucesso e de erro (TDD).

### Out-of-Scope
- Implementação das rotas FastAPI em `src/lumi/api/v1/` (atendidas em tarefas subsequentes).
- Camada de persistência ORM / SQLAlchemy e consultas no banco de dados pgvector.
