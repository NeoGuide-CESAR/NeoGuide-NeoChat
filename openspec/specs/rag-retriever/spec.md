# Spec: Recuperação Vetorial Semântica e Salvaguarda por Threshold (rag-retriever)

## Requirements

### Requirement: Recuperação Vetorial Semântica de Normas (NormativeRetriever)
O sistema DEVE prover uma classe assíncrona `NormativeRetriever` capaz de converter a consulta do usuário em vetor denso de embedding e recuperar os fragmentos normativos mais semanticamente similares persistidos no pgvector.

#### Scenario: Recuperação bem-sucedida de fragmentos relevantes
- **GIVEN** uma consulta técnica válida do usuário (ex.: "Qual o limite de demanda para fornecimento em tensão secundária?")
- **WHEN** o método `retrieve()` de `NormativeRetriever` for executado
- **THEN** ele deve gerar o embedding da consulta via `Embeddings.aembed_query` (ou fallback), consultar o `NormativeVectorStore.search_similar`, filtrar os chunks pelo threshold de similaridade e retornar um `RetrievalResult` contendo os chunks recuperados e `is_contingency=False`.

### Requirement: Salvaguarda Determinística de Relevância e Contingência
O sistema DEVE atuar como um *Retrieval Guardrail*, acionando resposta de contingência determinística quando nenhum fragmento atingir o limiar de similaridade especificado ou quando a busca não retornar resultados.

#### Scenario: Chunks abaixo do threshold de similaridade
- **GIVEN** uma consulta do usuário que gere fragmentos com scores de similaridade estritamente inferiores ao limiar (threshold padrão 0.70)
- **WHEN** o método `retrieve()` processar a busca
- **THEN** o `RetrievalResult` retornado deve possuir `is_contingency=True`, `chunks=[]` e `contingency_message` idêntico a `CONTINGENCY_NO_SOURCES_MESSAGE`.

#### Scenario: Base vetorial sem resultados para a busca
- **GIVEN** uma consulta cujo vetor não retorne nenhum registro do banco de dados
- **WHEN** o método `retrieve()` processar o retorno
- **THEN** o `RetrievalResult` retornado deve possuir `is_contingency=True`, `chunks=[]` e `contingency_message=CONTINGENCY_NO_SOURCES_MESSAGE`.

### Requirement: Validação e Gating de Query Vazia ou em Branco
O sistema DEVE interceptar e rejeitar imediatamente consultas vazias, nulas ou contendo apenas caracteres de espaço em branco antes de disparar embeddings ou queries no banco.

#### Scenario: Consulta em branco ou apenas espaços
- **GIVEN** uma string vazia `""` ou contendo espaços/tabulações/quebras `"   \t \n  "`
- **WHEN** o método `retrieve()` for invocado
- **THEN** ele deve retornar imediatamente `RetrievalResult` com `is_contingency=True`, `chunks=[]` e `contingency_message=CONTINGENCY_NO_SOURCES_MESSAGE`, sem invocar o gerador de embeddings nem o banco de dados.

### Requirement: Contrato Estruturado de Fragmento Recuperado (RetrievedChunk)
O sistema DEVE modelar os fragmentos recuperados através da dataclass `RetrievedChunk`, contendo identificadores da norma, título, revisão, localização hierárquica (seção e página), conteúdo textual e score de similaridade, além do método de conversão `to_source_metadata() -> SourceMetadata`.

#### Scenario: Conversão de RetrievedChunk para SourceMetadata
- **GIVEN** uma instância de `RetrievedChunk` com dados de documento normativo e similaridade
- **WHEN** o método `to_source_metadata()` for invocado
- **THEN** deve produzir um objeto `SourceMetadata` Pydantic válido com `document_code`, `revision`, `section`, `page`, `relevance_score` e `snippet`, com fallbacks seguros para seções e páginas ausentes.

### Requirement: Formatação Consistente de Contexto RAG (RetrievalResult)
O sistema DEVE fornecer na dataclass `RetrievalResult` a propriedade `formatted_context` para concatenação padronizada dos fragmentos normativos a serem injetados no prompt mestre da Lumi.

#### Scenario: Formatação de múltiplos fragmentos normativos
- **GIVEN** um `RetrievalResult` contendo um ou mais `RetrievedChunk`
- **WHEN** a propriedade `formatted_context` for lida
- **THEN** cada fragmento deve ser formatado como `[Fonte: {document_code}, Item {section_code}, Pág. {page_number}]\n{content}`, separados por `\n\n`.

#### Scenario: Formatação em caso de contingência
- **GIVEN** um `RetrievalResult` com `is_contingency=True` ou sem fragmentos
- **WHEN** a propriedade `formatted_context` for lida
- **THEN** deve retornar uma string vazia `""`.

### Requirement: Eager Loading de Documentos Relacionados no pgvector
O repositório vetorial `NormativeVectorStore` DEVE realizar eager loading da entidade `NormativeDocument` em `search_similar()` utilizando `selectinload(NormativeChunk.document)` para assegurar disponibilidade dos metadados da norma sem erros assíncronos de `MissingGreenlet`.

#### Scenario: Execução de search_similar com carregamento de relacionamento
- **GIVEN** uma busca semântica assíncrona por chunks no repositório `NormativeVectorStore`
- **WHEN** a consulta `search_similar()` for executada
- **THEN** os chunks retornados devem conter o relacionamento `.document` devidamente carregado via `selectinload`.

### Requirement: Configuração de Quantidade Padrão de Chunks (top_k_retrieval)
O sistema DEVE configurar o padrão de chunks a serem recuperados (`top_k_retrieval`) com valor igual a 10 no modelo de configurações centrais `Settings`.

#### Scenario: Leitura das configurações padrão de recuperação
- **GIVEN** uma instância de `Settings` padrão
- **WHEN** o campo `top_k_retrieval` for inspecionado
- **THEN** seu valor deve ser igual a 10.
