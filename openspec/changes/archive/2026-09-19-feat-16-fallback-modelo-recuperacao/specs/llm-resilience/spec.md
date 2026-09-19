# Delta Spec: Resiliência e Fallback de Modelos de Linguagem (LLM)

## ADDED Requirements

### Requirement: Cadeia de Fallback Automático de Modelos Gemini
O sistema DEVE implementar uma cadeia sequencial de recuperação automática de modelos generativos Google Gemini com ordem estrita de execução: modelo primário `gemini-3.8-flash`, primeiro fallback `gemini-3.7-flash` e segundo fallback `gemini-3.6-flash`. O mecanismo deve abranger execuções síncronas (`ChatService.process_chat`), transmissões streaming (`ChatService.stream_chat`) e reescrita contextual de queries (`QueryRewriter.rewrite`).

#### Scenario: Sucesso na Tentativa 1 com Modelo Primário
- **GIVEN** uma requisição de conversação ou reescrita e o modelo primário `gemini-3.8-flash` operacional
- **WHEN** o modelo primário for invocado
- **THEN** a resposta DEVE ser gerada pelo modelo primário na primeira tentativa (attempt=1) sem registrar eventos de fallback nem acionar modelos secundários.

#### Scenario: Recuperação no 1º Fallback após Falha do Modelo Primário
- **GIVEN** que o modelo primário `gemini-3.8-flash` retorne falha transitória (erro HTTP 503, 429 ou erro de conexão)
- **WHEN** a execução falhar antes da emissão de tokens
- **THEN** o sistema DEVE registrar log estruturado `logger.warning("llm_fallback_attempt", failed_model="gemini-3.8-flash", next_model="gemini-3.7-flash", attempt=1, error=...)` e invocar imediatamente `gemini-3.7-flash` como tentativa 2, retornando a resposta gerada com sucesso.

#### Scenario: Recuperação no 2º Fallback após Falhas em 3.8 e 3.7
- **GIVEN** que os modelos `gemini-3.8-flash` e `gemini-3.7-flash` apresentem falhas consecutivas
- **WHEN** a cadeia sequencial avançar para a tentativa 3
- **THEN** o sistema DEVE registrar as transições para as tentativas 1 e 2, executar o segundo fallback `gemini-3.6-flash` e retornar o resultado com sucesso.

#### Scenario: Esgotamento da Cadeia após Limite Estrito de 3 Tentativas
- **GIVEN** que os três modelos da cadeia (`gemini-3.8-flash`, `gemini-3.7-flash` e `gemini-3.6-flash`) falhem consecutivamente
- **WHEN** a 3ª tentativa for frustrada
- **THEN** o sistema DEVE interromper a execução sem exceder 3 tentativas no total e lançar `HTTPException` com código de status HTTP 503 (Service Unavailable) contendo mensagem explicativa de sobrecarga temporária.

#### Scenario: Observabilidade Estruturada das Tentativas de Fallback
- **GIVEN** qualquer exceção transitória que demande a ativação de um modelo subsequente
- **WHEN** o fallback for acionado
- **THEN** o sistema DEVE emitir evento estruturado via `structlog` com nome `llm_fallback_attempt`, contendo os atributos `failed_model`, `next_model`, `attempt` e `error`.
