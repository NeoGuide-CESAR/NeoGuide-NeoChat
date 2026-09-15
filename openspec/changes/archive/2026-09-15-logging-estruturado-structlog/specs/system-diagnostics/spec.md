# Delta Spec: Logging Estruturado com structlog e Rastreabilidade de Requisições

## ADDED Requirements

### Requirement: Logging Estruturado Centralizado com structlog
O sistema DEVE fornecer configuração central de logging estruturado baseada na biblioteca `structlog`, com processamento de contextvars, formatação de nível de log, timestamps em padrão ISO, renderização de exceções e stack traces, e unificação com os logs da standard library (`uvicorn`, `uvicorn.access`, `uvicorn.error`, `sqlalchemy.engine`).

#### Scenario: Renderização em JSON para Produção e Staging
- **GIVEN** a configuração de logging inicializada com ambiente `"production"` ou `"staging"`
- **WHEN** uma mensagem de log for emitida via structlog ou standard library
- **THEN** a saída DEVE ser formatada como um objeto JSON válido contendo ao menos os campos `event`, `level` e `timestamp`.

#### Scenario: Renderização em Console Colorido para Desenvolvimento
- **GIVEN** a configuração de logging inicializada com ambiente `"development"` ou local
- **WHEN** uma mensagem de log for emitida
- **THEN** a saída DEVE utilizar o formatador legível de terminal `ConsoleRenderer` com cores habilitadas.

#### Scenario: Integração e Unificação com Logs da Standard Library
- **GIVEN** a inicialização do `setup_logging()`
- **WHEN** módulos terceiros como `uvicorn` ou `sqlalchemy.engine` emitirem logs via `logging.getLogger`
- **THEN** os eventos DEVEM ser interceptados pelo `ProcessorFormatter` e formatados na mesma estrutura padronizada dos logs da aplicação.

---

### Requirement: Blindagem e Mascaramento Defensivo de Dados Sensíveis (Redaction)
O pipeline de logging DEVE interceptar e mascarar automaticamente valores associados a chaves que contenham credenciais ou informações confidenciais, substituindo-os pela constante `"[REDACTED]"`.

#### Scenario: Mascaramento de Chaves Sensíveis em Qualquer Nível de Profundidade
- **GIVEN** uma chamada de log estruturado contendo chaves como `api_key`, `x-api-key`, `authorization`, `password`, `token`, `secret`, `access_token` ou `cookie`
- **WHEN** o processador `redact_sensitive_data` processar o dicionário de evento
- **THEN** os valores dessas chaves DEVEM ser substituídos por `"[REDACTED]"`
- **AND** a verificação DEVE ser insensível a maiúsculas/minúsculas (case-insensitive)
- **AND** o mascaramento DEVE alcançar dicionários e listas aninhadas sem alterar os campos não sensíveis.

---

### Requirement: Rastreabilidade e Correlação de Requisições HTTP (CorrelationIdMiddleware)
O sistema DEVE vincular um identificador único de correlação a cada requisição HTTP recebida, registrando métricas de latência e propagando o identificador no ciclo assíncrono.

#### Scenario: Requisição sem X-Request-ID fornecido
- **GIVEN** uma requisição HTTP enviada sem o cabeçalho `X-Request-ID`
- **WHEN** o `CorrelationIdMiddleware` interceptar a requisição
- **THEN** o middleware DEVE gerar um novo identificador UUIDv4
- **AND** associar o identificador ao contexto assíncrono via `structlog.contextvars.bind_contextvars(request_id=...)`
- **AND** injetar o cabeçalho `X-Request-ID` na resposta HTTP retornada ao cliente.

#### Scenario: Requisição com X-Request-ID pré-existente
- **GIVEN** uma requisição HTTP enviada com o cabeçalho `X-Request-ID: meu-rastreio-123`
- **WHEN** o `CorrelationIdMiddleware` processar a requisição
- **THEN** o middleware DEVE preservar o valor fornecido (`meu-rastreio-123`)
- **AND** vinculá-lo ao contexto e refleti-lo no cabeçalho da resposta.

#### Scenario: Registro de Ciclo de Vida da Requisição e Limpeza Contextual
- **GIVEN** uma requisição HTTP processada pela API
- **WHEN** o fluxo de execução passar pelo `CorrelationIdMiddleware`
- **THEN** um log de início DEVE ser emitido contendo `method` e caminho/rota
- **AND** após a conclusão, um log de finalização DEVE ser emitido contendo `method`, caminho/rota, `status_code` e `duration_ms`
- **AND** o contexto assíncrono DEVE ser limpo via `clear_contextvars()` no bloco `finally`.
