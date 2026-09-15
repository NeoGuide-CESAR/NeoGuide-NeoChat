# Delta Spec: Segurança da API, Autenticação, Rate-Limiting e CORS

## ADDED Requirements

### Requirement: Autenticação por Chave de API (X-API-Key)
A API DEVE exigir um header HTTP `X-API-Key` em endpoints protegidos e validar seu valor contra a chave definida nas configurações (`settings.api_key`). Tentativas com chave ausente ou incorreta devem ser rejeitadas com código HTTP 401 Unauthorized e mensagem descritiva padronizada.

#### Scenario: Requisição sem header X-API-Key
- **GIVEN** um endpoint protegido pela dependência de autenticação
- **WHEN** uma requisição HTTP for enviada sem o header `X-API-Key`
- **THEN** a resposta deve retornar status HTTP 401 Unauthorized com o payload JSON `{"detail": "Invalid or missing API Key"}`.

#### Scenario: Requisição com header X-API-Key inválido
- **GIVEN** um endpoint protegido pela dependência de autenticação
- **WHEN** uma requisição HTTP for enviada com o header `X-API-Key: chave-invalida`
- **THEN** a resposta deve retornar status HTTP 401 Unauthorized com o payload JSON `{"detail": "Invalid or missing API Key"}`.

#### Scenario: Requisição com header X-API-Key válido
- **GIVEN** um endpoint protegido pela dependência de autenticação
- **WHEN** uma requisição HTTP for enviada com o header `X-API-Key` correspondente à chave configurada em `settings.api_key`
- **THEN** a requisição deve ser autorizada e retornar status HTTP 200 OK com os dados do endpoint.

### Requirement: Rate-Limiting com Janela Deslizante
A API DEVE limitar a taxa de requisições por chave de API utilizando um mecanismo de janela deslizante (sliding window) em memória, thread-safe e assíncrono. O limite padrão deve ser parametrizável via `settings.rate_limit_requests_per_minute`. Requisições que excederem o limite devem receber resposta HTTP 429 Too Many Requests com cabeçalho `Retry-After`.

#### Scenario: Rajada de requisições excedendo o limite por minuto
- **GIVEN** um limitador configurado para N requisições por minuto
- **WHEN** um cliente autenticado enviar N + 1 requisições dentro do mesmo intervalo de 60 segundos
- **THEN** a (N+1)-ésima requisição deve retornar status HTTP 429 Too Many Requests, contendo mensagem de limite excedido e cabeçalho `Retry-After`.

#### Scenario: Liberação após passagem da janela ou reset
- **GIVEN** um cliente que atingiu o limite de requisições por minuto
- **WHEN** o tempo de expiração da janela decorrer ou o limitador for explicitamente resetado
- **THEN** novas requisições com a mesma chave devem ser processadas com sucesso (HTTP 200).

### Requirement: Middleware de Compartilhamento de Recursos (CORS)
A aplicação FastAPI DEVE possuir o `CORSMiddleware` ativo, restringindo as origens permitidas àquelas declaradas em `settings.cors_origins` e respondendo adequadamente a requisições de preflight HTTP OPTIONS.

#### Scenario: Requisição preflight OPTIONS com origem permitida
- **GIVEN** a aplicação FastAPI em execução com `settings.cors_origins` configurado
- **WHEN** uma requisição HTTP OPTIONS for enviada com cabeçalhos `Origin: http://localhost:3000` e `Access-Control-Request-Method: GET`
- **THEN** a resposta deve retornar status HTTP 200 OK com o cabeçalho `Access-Control-Allow-Origin: http://localhost:3000`.

#### Scenario: Requisição com origem não autorizada
- **GIVEN** a aplicação FastAPI em execução com origens restritas
- **WHEN** uma requisição for enviada com `Origin: http://origem-desconhecida-maliciosa.com`
- **THEN** o cabeçalho `Access-Control-Allow-Origin` não deve conter a origem não autorizada.

### Requirement: Endpoint de Verificação de Autenticação
A API DEVE disponibilizar o endpoint `GET /api/v1/auth/check` protegido pela dependência combinada `api_key_and_rate_limit` para validar a conectividade e integridade da chave do cliente.

#### Scenario: Verificação bem-sucedida de credenciais
- **GIVEN** o endpoint `GET /api/v1/auth/check`
- **WHEN** uma requisição autenticada com chave válida for enviada
- **THEN** deve retornar status HTTP 200 OK com a confirmação de autenticação.
