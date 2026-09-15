# Design: Fábrica de Provedores de LLM e Embeddings Desacoplada

## Context & Architecture
Em conformidade com o requisito não-funcional RNF-06 (Portabilidade de LLMs) e com a estrutura do pacote `src/lumi/rag/`, a fábrica de LLMs e Embeddings fornece interfaces de criação centralizadas e desacopladas de classes de provedores concretos. A arquitetura segue o padrão *Factory Method / Parameterized Factory*.

### Layout de Componentes
```
src/lumi/
├── core/
│   └── config.py               # Settings com default_llm_provider e default_embedding_provider
└── rag/
    ├── __init__.py             # Exporta get_llm, get_embeddings, validate_embedding_dimension
    └── llm_factory.py          # Implementação das funções de fábrica e validações
```

## Decisions & Patterns

### 1. Padrão de Fábrica Parametrizada
- `get_llm(provider: str | None = None, settings: Settings | None = None, **kwargs: Any) -> BaseChatModel`:
  - Se `provider` não for informado, lê `settings.default_llm_provider` (padrão `"gemini"`).
  - Trata strings normalizadas (letras minúsculas e sem espaços laterais).
  - Fornece suporte nativo a:
    - `"gemini"`: retorna `ChatGoogleGenerativeAI(model=..., google_api_key=..., **kwargs)`.
    - `"claude"` ou `"anthropic"`: retorna `ChatAnthropic(model=..., api_key=..., **kwargs)`.
  - Levanta `ValueError` explicativo se o provedor não for reconhecido.
  - Passa `kwargs` adicionais permitindo ajustar `temperature`, `max_tokens`, etc.

### 2. Fábrica de Embeddings com Suporte a Testes
- `get_embeddings(provider: str | None = None, settings: Settings | None = None, **kwargs: Any) -> Embeddings`:
  - Se `provider` não for informado, lê `settings.default_embedding_provider` (padrão `"gemini"`).
  - Fornece suporte a:
    - `"gemini"`: retorna `GoogleGenerativeAIEmbeddings(model=..., google_api_key=..., **kwargs)`.
    - `"fake"`: retorna `FakeEmbeddings(size=settings.embedding_dimension, **kwargs)`.
  - Levanta `ValueError` se o provedor não for suportado.

### 3. Validação de Dimensionalidade Vetorial
- `validate_embedding_dimension(embedding: Sequence[float] | list[float], expected_dimension: int | None = None, settings: Settings | None = None) -> bool`:
  - Garante que a dimensionalidade do vetor coincida exatamente com a esperada (padrão `settings.embedding_dimension = 768`).
  - Lança `ValueError` em caso de incompatibilidade, prevenindo inserções corrompidas no pgvector.

### 4. Estratégia de Testes Unitários Sem Rede (Mocking)
- Todos os testes unitários utilizam chaves de API mockadas e monkeypatching/mocks quando apropriado para assegurar isolamento absoluto e ausência de chamadas HTTP externas durante a execução do pytest.
- Utilização de `FakeEmbeddings` para testes de RAG e indexação vetorial.
