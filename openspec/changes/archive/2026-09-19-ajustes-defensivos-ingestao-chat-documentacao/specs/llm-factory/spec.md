# Delta Spec: Fábrica de Provedores de LLM e Embeddings

## ADDED Requirements

### Requirement: Configuração Explícita de Dimensionalidade Vetorial no Gemini Embeddings
Ao instanciar o gerador de embeddings Google Gemini (`GoogleGenerativeAIEmbeddings`), o módulo DEVE definir o argumento `output_dimensionality` com o valor configurado em `Settings.embedding_dimension` (768), prevenindo divergências na dimensão do vetor gerado caso o modelo padrão da biblioteca seja atualizado.

#### Scenario: Instanciação padrão de embeddings Gemini com dimensão explícita
- **GIVEN** a função `get_embeddings` executada para o provedor Gemini
- **WHEN** os argumentos forem repassados para `GoogleGenerativeAIEmbeddings`
- **THEN** o parâmetro `output_dimensionality` deve ser injetado com o valor de `settings.embedding_dimension` caso não tenha sido explicitamente customizado.
