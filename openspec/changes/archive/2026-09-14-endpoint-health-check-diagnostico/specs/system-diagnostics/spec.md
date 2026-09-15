# Spec: Diagnóstico de Sistema e Health Check de Conectividade

## Requirements

### Requirement: Sonda de Liveness Básica não autenticada
O sistema DEVE disponibilizar uma rota `GET /health` pública na raiz da API sem exigência de autenticação por API Key, retornando status básico do processo HTTP para uso em balanceadores de carga e orquestradores de contêineres.

#### Scenario: Requisição de liveness bem-sucedida
- **GIVEN** a API Lumi em execução
- **WHEN** uma requisição HTTP `GET /health` for enviada sem cabeçalhos de autenticação
- **THEN** a resposta DEVE retornar código HTTP 200
- **AND** o corpo JSON DEVE conter `status: "healthy"` e a versão da aplicação.

---

### Requirement: Proteção de Acesso ao Diagnóstico Avançado
O sistema DEVE restringir o acesso ao endpoint `/api/v1/health` exigindo um cabeçalho `X-API-Key` válido e controle de taxa de requisições.

#### Scenario: Acesso a `/api/v1/health` sem API Key
- **GIVEN** o endpoint `/api/v1/health` ativo
- **WHEN** uma requisição for enviada sem o cabeçalho `X-API-Key`
- **THEN** a resposta DEVE retornar código HTTP 401 Unauthorized
- **AND** a mensagem de erro DEVE indicar chave ausente ou inválida.

#### Scenario: Acesso a `/api/v1/health` com API Key inválida
- **GIVEN** o endpoint `/api/v1/health` ativo e uma chave inválida fornecida
- **WHEN** uma requisição for enviada com cabeçalho `X-API-Key: chave-invalida`
- **THEN** a resposta DEVE retornar código HTTP 401 Unauthorized.

---

### Requirement: Diagnóstico de Conectividade com Banco de Dados e Extensão pgvector
O sistema DEVE executar um diagnóstico ativo e assíncrono sobre a conexão com o PostgreSQL, calculando a latência de execução (`SELECT 1`) e verificando a instalação e versão da extensão `pgvector`.

#### Scenario: Banco de dados saudável e pgvector instalado
- **GIVEN** a infraestrutura PostgreSQL operacional com a extensão `pgvector` instalada
- **AND** uma requisição autorizada com `X-API-Key` válida para `GET /api/v1/health`
- **WHEN** o diagnóstico for executado
- **THEN** a resposta DEVE retornar código HTTP 200
- **AND** o campo `status` DEVE ser `"healthy"`
- **AND** o campo `database.status` DEVE ser `"connected"`
- **AND** `database.latency_ms` DEVE ser um número de ponto flutuante não nulo
- **AND** `database.pgvector_installed` DEVE ser `true`
- **AND** `database.pgvector_version` DEVE conter a versão da extensão (ex.: `"0.7.0"`).

#### Scenario: Banco de dados operacional porém extensão pgvector ausente
- **GIVEN** o PostgreSQL conectado e respondendo a `SELECT 1` porém sem a extensão `pgvector` registrada
- **WHEN** uma requisição autorizada para `GET /api/v1/health` for processada
- **THEN** a resposta DEVE retornar código HTTP 200
- **AND** o campo `status` DEVE indicar `"degraded"`
- **AND** `database.status` DEVE ser `"connected"`
- **AND** `database.pgvector_installed` DEVE ser `false`
- **AND** `database.pgvector_version` DEVE ser `null`.

#### Scenario: Falha de conexão ou timeout com o banco de dados
- **GIVEN** o banco de dados inacessível ou levantando erro operacional de conexão
- **WHEN** uma requisição autorizada para `GET /api/v1/health` for processada
- **THEN** a resposta DEVE capturar a falha defensivamente e retornar código HTTP 503 Service Unavailable
- **AND** o campo `status` DEVE ser `"unhealthy"`
- **AND** o campo `database.status` DEVE ser `"error"`
- **AND** o campo `database.error` DEVE conter uma mensagem de erro sanitizada que não exponha senhas ou dados sensíveis de conexão.
