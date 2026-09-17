# Spec: Suíte de Testes Automatizados, Integração de API e Cobertura de Código

## Requirements

### Requirement: Registro de Markers e Configuração de Cobertura
O sistema DEVE configurar o `pytest` para registrar formalmente os markers `integration` (para testes que interagem com o banco de dados e endpoints HTTP) e `evals` (para avaliações de fidelidade RAG e métricas Ragas), rejeitando markers desconhecidos através de `--strict-markers`. O ambiente de desenvolvimento DEVE disponibilizar `pytest-cov>=5.0.0` para relatório detalhado de cobertura de linhas e branches com meta estrita >= 95%.

#### Scenario: Execução de testes com marcadores estritos
- **GIVEN** a configuração de testes no `pyproject.toml`
- **WHEN** o comando `pytest` for executado com marcadores não registrados
- **THEN** o `pytest` deve falhar imediatamente informando que o marker é desconhecido.

#### Scenario: Execução de medição de cobertura
- **GIVEN** a suíte de testes unitários e de integração
- **WHEN** o comando `pytest --cov=src/lumi --cov-report=term-missing` for executado
- **THEN** deve gerar um relatório detalhado de cobertura por módulo e reportar cobertura global igual ou superior a 95%.

### Requirement: Fixture de Banco de Dados com Rollback Transacional e Skip Gracioso
O sistema DEVE prover fixtures assíncronas em `tests/conftest.py` para testes de integração (`db_session`). A fixture DEVE testar a conectividade assíncrona com o PostgreSQL/pgvector. Se o banco de dados não estiver ativo ou não puder ser contactado, a fixture DEVE acionar `pytest.skip("PostgreSQL/pgvector não disponível no ambiente")` sem gerar falsos negativos na suíte. Se o banco estiver acessível, a fixture DEVE abrir uma transação assíncrona e executar rollback automático ao final do teste, garantindo idempotência e isolamento.

#### Scenario: Execução em ambiente sem banco de dados ativo
- **GIVEN** um ambiente de desenvolvimento ou CI onde o container do PostgreSQL não está em execução
- **WHEN** qualquer teste dependente da fixture `db_session` for executado
- **THEN** o teste deve ser ignorado graciosamente com mensagem explicativa via `pytest.skip`.

#### Scenario: Execução em ambiente com PostgreSQL ativo
- **GIVEN** um container PostgreSQL com extensão pgvector em execução
- **WHEN** um teste inserir registros via `db_session`
- **THEN** os dados devem estar acessíveis durante o teste e completamente descartados via rollback ao término do teste.

### Requirement: Testes de Busca Vetorial pgvector
O sistema DEVE validar a busca vetorial por similaridade de cosseno em `tests/integration/test_vector_search.py` com o marker `@pytest.mark.integration`. Os testes DEVEM validar:
1. Inserção de documentos e chunks com tensores de embeddings via `NormativeVectorStore`.
2. Busca por similaridade de cosseno retornando os chunks mais relevantes.
3. Descarte de chunks com similaridade inferior ao limiar de corte de 0.70.
4. Isolamento estrito de busca quando filtrado por código específico de norma técnica (`document_code`).

#### Scenario: Busca semântica e limiar de similaridade 0.70
- **GIVEN** chunks inseridos no pgvector com similaridades calculadas de 0.90 e 0.50 em relação ao vetor de busca
- **WHEN** o método `search_similar(query_embedding, threshold=0.70)` for executado
- **THEN** apenas o chunk com similaridade 0.90 deve ser retornado, e o chunk com similaridade 0.50 deve ser descartado.

#### Scenario: Isolamento de chunks por código de documento
- **GIVEN** chunks pertencentes às normas `DIS-NOR-030` e `DIS-NOR-053`
- **WHEN** o método `search_similar(query_embedding, document_code="DIS-NOR-030")` for executado
- **THEN** apenas os chunks vinculados à norma `DIS-NOR-030` devem ser retornados.

### Requirement: Validação Ponta a Ponta de Fluxo E2E
O sistema DEVE prover um teste de integração de fluxo completo em `tests/integration/test_e2e_flow.py` que valide a jornada do usuário e dos subsistemas integrados:
1. Verificação de prontidão e saúde no endpoint `GET /health`.
2. Criação de nova sessão de atendimento via `POST /api/v1/sessions`.
3. Envio de primeira pergunta via `POST /api/v1/chat` com streaming SSE, consumindo eventos `token`, `sources` e `done`.
4. Envio de segunda pergunta (multi-turn) garantindo resolução contextual, histórico e fontes normativas.
5. Verificação de telemetria assíncrona registrada em `normative_query_analytics`.
6. Validação de expiração por inatividade (TTL de 1 hora) e consulta de detalhes da sessão.

#### Scenario: Ciclo de vida completo de atendimento e auditoria
- **GIVEN** um cliente autenticado com chave de API válida
- **WHEN** executar sucessivamente verificação de saúde, criação de sessão, turnos de chat com streaming SSE e consulta de histórico
- **THEN** todos os status HTTP devem ser bem-sucedidos (200/201), os eventos de SSE devem respeitar o schema, a persistência assíncrona de telemetria analítica deve ser acionada e o status da sessão deve refletir os turnos gravados.
