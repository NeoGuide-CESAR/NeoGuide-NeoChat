# Spec: Fábrica de Provedores de LLM e Embeddings

## Requirements

### Requirement: Instanciação Desacoplada de Modelos de Linguagem (LLM)
O módulo `lumi.rag.llm_factory` DEVE fornecer a função `get_llm(provider: str | None = None, settings: Settings | None = None, **kwargs: Any)` para instanciar instâncias compatíveis com `BaseChatModel` da LangChain com base no provedor solicitado ou no valor configurado em `Settings.default_llm_provider`.

#### Scenario: Instanciação do Provedor Gemini (Primário)
- **GIVEN** a fábrica `get_llm` e configurações com `gemini_api_key` e `gemini_model` válidos
- **WHEN** invocada com `provider="gemini"` ou com `provider=None` quando o padrão for `"gemini"`
- **THEN** deve retornar uma instância de `ChatGoogleGenerativeAI` configurada com o modelo e a chave de API fornecidos.

#### Scenario: Instanciação do Provedor Claude / Anthropic (Alternativo)
- **GIVEN** a fábrica `get_llm` e configurações com `anthropic_api_key` e `anthropic_model` válidos
- **WHEN** invocada com `provider="claude"` ou `provider="anthropic"`
- **THEN** deve retornar uma instância de `ChatAnthropic` configurada com o modelo e a chave de API fornecidos.

#### Scenario: Rejeição de Provedor de LLM Não Suportado
- **GIVEN** a fábrica `get_llm`
- **WHEN** invocada com um nome de provedor inválido ou não suportado (ex.: `"openai"`, `"invalido"`)
- **THEN** deve lançar `ValueError` contendo mensagem explicativa indicando os provedores suportados (`gemini`, `claude`/`anthropic`).

### Requirement: Instanciação Desacoplada de Modelos de Embeddings
O módulo `lumi.rag.llm_factory` DEVE fornecer a função `get_embeddings(provider: str | None = None, settings: Settings | None = None, **kwargs: Any)` para instanciar geradores de embeddings compatíveis com `Embeddings` da LangChain.

#### Scenario: Instanciação de Embeddings Gemini
- **GIVEN** a fábrica `get_embeddings` e configurações com `gemini_api_key` e `gemini_embedding_model`
- **WHEN** invocada com `provider="gemini"` ou com `provider=None` quando o padrão for `"gemini"`
- **THEN** deve retornar uma instância de `GoogleGenerativeAIEmbeddings` configurada com o modelo e chave especificados.

#### Scenario: Instanciação de FakeEmbeddings para Testes
- **GIVEN** a fábrica `get_embeddings` e configurações com `embedding_dimension` (768)
- **WHEN** invocada com `provider="fake"`
- **THEN** deve retornar uma instância de `FakeEmbeddings` configurada com tamanho de vetor igual a 768, sem depender de chamadas remotas de API.

#### Scenario: Rejeição de Provedor de Embeddings Inválido
- **GIVEN** a fábrica `get_embeddings`
- **WHEN** invocada com um provedor inválido (ex.: `"invalido"`, `"cohere"`)
- **THEN** deve lançar `ValueError` explicitando os provedores válidos (`gemini`, `fake`).

### Requirement: Validação de Dimensionalidade Vetorial
O módulo `lumi.rag.llm_factory` DEVE fornecer a função `validate_embedding_dimension(embedding: Sequence[float] | list[float], expected_dimension: int | None = None, settings: Settings | None = None) -> bool` para assegurar que os vetores gerados atendam à dimensão exigida pelo esquema do pgvector (768).

#### Scenario: Vetor com Dimensão Correta (768)
- **GIVEN** um vetor com exatamente 768 dimensões numéricas
- **WHEN** submetido à validação com dimensão esperada 768
- **THEN** a função deve retornar `True`.

#### Scenario: Vetor com Dimensão Incompatível
- **GIVEN** um vetor com dimensão diferente de 768 (ex.: 512 ou 1536)
- **WHEN** submetido à validação
- **THEN** a função deve lançar `ValueError` indicando a dimensão esperada e a dimensão recebida.
