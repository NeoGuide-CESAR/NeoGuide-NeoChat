# Delta Spec: Ingestão, Higienização e Parsing de Documentos Normativos

## ADDED Requirements

### Requirement: Tratamento Defensivo de Rate Limiting e Backoff Adaptativo de Embeddings
O pipeline de ingestão DEVE implementar retentativas automáticas e cálculo adaptativo de backoff na geração de embeddings quando a API de inteligência artificial retornar erro de cota excedida (`ResourceExhausted` / HTTP 429). O sistema DEVE extrair a recomendação de tempo de espera indicada pelo provedor (através da função `_extract_retry_delay`), exibir notificação de progresso informativa no terminal e aguardar antes de reiniciar o lote.

#### Scenario: Detecção de cota da API do Google com pausa adaptativa
- **GIVEN** um erro de taxa de requisições excedida (`ResourceExhausted` ou HTTP 429) durante a vetorização de um lote
- **WHEN** a exceção for capturada pelo pipeline
- **THEN** o sistema deve extrair o tempo de espera recomendado (ou utilizar backoff pré-definido caso não encontrado), registrar aviso estruturado de log, emitir aviso no terminal e pausar a execução assincronamente pelo tempo determinado sem abortar a ingestão.

### Requirement: Desduplicação e Priorização de Formatos na Ingestão por Diretório
Ao escanear um diretório com a opção `--all` ou indicando uma pasta, caso coexistam arquivos normativos com o mesmo radical (`stem`) nos formatos `.md` e `.pdf`, o pipeline DEVE priorizar o arquivo `.md` e descartar o `.pdf` correspondente da fila de processamento, evitando duplicidade de vetores no banco de dados.

#### Scenario: Coexistência de norma em Markdown e PDF na mesma pasta
- **GIVEN** uma pasta contendo `DIS-NOR-030-REV07.md` e `DIS-NOR-030-REV07.pdf`
- **WHEN** o pipeline de ingestão listar os arquivos normativos a processar
- **THEN** apenas a versão `DIS-NOR-030-REV07.md` deve ser enfileirada para parser e vetorização.

## MODIFIED Requirements

### Requirement: Extração de Metadados de PDF e Heurística de Revisão
#### Scenario: Rejeição de tokens inválidos na revisão normativa de PDF
- **WHEN** o texto extraído da primeira página contiver marcações de layout capturadas como revisão (ex.: `"Nº"`, `"NO"`, `"PÁG"`)
- **THEN** o parser deve ignorar esses termos espúrios e extrair o número da revisão a partir do nome do arquivo (ex.: `REV07`) ou adotar `REV01` como contingência segura.
