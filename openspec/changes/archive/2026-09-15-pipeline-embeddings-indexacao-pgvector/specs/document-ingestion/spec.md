# Delta Spec: Ingestão, Embeddings Vetoriais e Indexação HNSW no pgvector

## Added Requirements

### Requirement: Repositório Vetorial Normativo (NormativeVectorStore)
O sistema DEVE fornecer a classe `NormativeVectorStore` vinculada a uma sessão assíncrona SQLAlchemy (`AsyncSession`), oferecendo operações transacionais de persistência atômica e recuperação vetorial por similaridade de cosseno com índice HNSW.

#### Scenario: Inserção atômica de novo documento com chunks e tensores
- **GIVEN** um código de documento `"DIS-NOR-030"`, título, revisão `"07"`, uma lista de instâncias `NormativeChunkData` e uma lista correspondente de vetores de embedding de 768 dimensões
- **WHEN** o método `upsert_document_with_chunks` for executado
- **THEN** o registro correspondente em `NormativeDocument` deve ser criado ou localizado, e todos os chunks devem ser gravados em lote na tabela `normative_chunks` com seus metadados JSONB e tensores vetoriais, retornando a contagem de chunks inseridos.

#### Scenario: Idempotência estrita e eliminação de resíduos anteriores
- **GIVEN** que o documento `"DIS-NOR-030"` já possua chunks previamente persistidos no banco
- **WHEN** `upsert_document_with_chunks` for acionado novamente para `"DIS-NOR-030"`
- **THEN** todos os chunks associados anteriormente ao identificador do documento devem ser excluídos antes da inserção dos novos blocos, prevenindo duplicações ou resíduos órfãos.

#### Scenario: Busca vetorial por similaridade com threshold e top-k
- **GIVEN** um vetor de embedding de consulta, um `top_k = 5` e um limiar mínimo de similaridade `threshold = 0.70`
- **WHEN** o método `search_similar` for acionado
- **THEN** os chunks devem ser recuperados utilizando o operador de distância de cosseno `<=>` do pgvector, convertendo para similaridade `(1.0 - distance)`, filtrando registros onde `similarity >= 0.70`, ordenados por proximidade e limitados a 5 resultados.

#### Scenario: Busca vetorial restrita por código de documento
- **GIVEN** uma consulta com vetor de embedding e o parâmetro `document_code = "DIS-NOR-053"`
- **WHEN** o método `search_similar` for executado
- **THEN** a consulta deve realizar join com `NormativeDocument` e retornar exclusivamente chunks associados à norma `"DIS-NOR-053"`.

---

### Requirement: Orquestrador de Ingestão e Geração de Embeddings em Lotes
O sistema DEVE fornecer a função assíncrona `ingest_normative_file` e utilitários de loteamento capazes de orquestrar a leitura, parsing, chunking híbrido, geração de embeddings com rate limiting defensivo / retentativas exponenciais e persistência vetorial.

#### Scenario: Ingestão de documento Markdown com provedor Fake
- **GIVEN** o caminho para o arquivo `DIS-NOR-030-REV07.md` e o provedor `"fake"`
- **WHEN** a função `ingest_normative_file` for executada
- **THEN** o documento deve ser parseado, chunkado, os vetores gerados em lotes e persistidos via `NormativeVectorStore`, retornando um objeto `IngestionResult` com `status = "success"`, código da norma, revisão, contagem de chunks e duração em segundos.

#### Scenario: Rate limiting defensivo e retentativas exponenciais
- **GIVEN** um conjunto de textos normativos e um provedor de embeddings sujeito a falhas transitórias de conexão ou limite de requisições (429)
- **WHEN** a geração em lote for acionada
- **THEN** o sistema deve processar em lotes (`batch_size=32`), aguardar delay defensivo entre lotes (0.2s) e executar até 3 tentativas com backoff exponencial (1s, 2s, 4s) antes de considerar o lote com falha.

---

### Requirement: Ponto de Entrada CLI para Ingestão Normativa
O sistema DEVE fornecer um ponto de entrada executável de linha de comando (`python -m lumi.ingestion.pipeline`) permitindo que operadores processem normas técnicas individuais ou varram diretórios completos em lote.

#### Scenario: Execução de arquivo individual via CLI
- **GIVEN** o comando `python -m lumi.ingestion.pipeline docs/info/DIS-NOR-030-REV07.md --provider fake`
- **WHEN** o processo for executado
- **THEN** o arquivo deve ser processado e um sumário com documento, revisão, total de chunks e tempo de ingestão deve ser impresso no console.

#### Scenario: Execução recursiva de diretório com a flag --all
- **GIVEN** um diretório contendo arquivos `.md` e `.pdf` e o comando com `--all`
- **WHEN** o CLI for executado
- **THEN** todos os arquivos normativos suportados dentro do diretório devem ser descobertos e ingeridos sequencialmente, apresentando um relatório consolidado.
