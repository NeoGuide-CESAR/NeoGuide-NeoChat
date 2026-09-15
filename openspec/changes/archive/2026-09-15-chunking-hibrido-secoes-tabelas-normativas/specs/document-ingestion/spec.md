# Spec Delta: Chunking Híbrido Semântico Orientado a Seções e Tabelas Normativas

## Requirements

### Requirement: Modelo Pydantic para Chunks Normativos Estruturados
O sistema DEVE representar fragmentos normativos através do modelo Pydantic v2 estrito `NormativeChunkData`, contendo o código do documento, revisão, conteúdo integral com breadcrumb, identificação de seção, número de página, metadados especializados (como `is_table`, `table_id`, `page_range`) e hash SHA-256 para garantia de idempotência.

#### Scenario: Instanciação de chunk normativo válido
- **GIVEN** código do documento `"DIS-NOR-030"`, revisão `"07"`, conteúdo com cabeçalho de breadcrumb, código de seção `"5.2"` e página `5`
- **WHEN** o modelo `NormativeChunkData` for instanciado
- **THEN** todos os campos devem ser validados e o `chunk_hash` SHA-256 correspondente deve estar preenchido.

#### Scenario: Validação de página e imutabilidade
- **GIVEN** tentativa de instanciar `NormativeChunkData` com `page_number = 0` ou alterar atributos após criação
- **WHEN** o Pydantic for executado
- **THEN** deve rejeitar páginas inválidas (< 1) e prevenir modificações em atributos (modelo imutável).

---

### Requirement: Particionamento Semântico Estrutural por Seções (Camada 1)
O sistema DEVE particionar documentos normativos respeitando a hierarquia de títulos e itens técnicos (`1.`, `5.2`, `6.7.16`, `Capítulo X`, `Anexo`), mantendo o rastreamento dinâmico da pilha de seções ativas.

#### Scenario: Rastreamento hierárquico de subseções
- **GIVEN** um documento contendo `### 5. DEFINIÇÕES` seguido por `### 5.1 Distribuidora` e `### 5.2 Distribuidoras Nordeste`
- **WHEN** a função `chunk_document` for executada
- **THEN** o chunk do item 5.1 deve conter `section_code = "5.1"`, `section_title = "Distribuidora"` e o chunk do item 5.2 deve conter `section_code = "5.2"`, `section_title = "Distribuidoras Nordeste"`.

---

### Requirement: Detecção Contínua de Marcadores de Página
O sistema DEVE detectar marcadores `**[Página X]**` ao longo do texto e associar a página correspondente a cada chunk, registrando `metadata["page_range"] = [X, Y]` quando um bloco cruzar fronteiras de páginas.

#### Scenario: Bloco textual que abrange múltiplas páginas
- **GIVEN** um parágrafo que se inicia na página 1 e prossegue na página 2 após o marcador `**[Página 2]**`
- **WHEN** a segmentação for gerada
- **THEN** o chunk resultante deve possuir `page_number = 1` e `metadata["page_range"] = [1, 2]`.

---

### Requirement: Tratamento Especializado de Tabelas Markdown
O sistema DEVE isolar tabelas Markdown em chunks dedicados com `metadata["is_table"] = True` e `metadata["table_id"]`. Tabelas de até ~2000 caracteres devem ser mantidas atômicas. Tabelas que excedam esse limite devem ser fracionadas logicamente por linhas com **replicação obrigatória das linhas de cabeçalho Markdown** em cada sub-chunk gerado.

#### Scenario: Tabela normativa atômica
- **GIVEN** uma tabela Markdown de 500 caracteres
- **WHEN** a função `chunk_document` for executada
- **THEN** a tabela deve gerar um único chunk com `metadata["is_table"] = True` e `metadata["table_id"]` definido.

#### Scenario: Tabela gigante com replicação de cabeçalho
- **GIVEN** uma tabela Markdown extensa com mais de 2500 caracteres e múltiplas linhas de dados
- **WHEN** a função `chunk_document` for executada
- **THEN** a tabela deve ser dividida em múltiplos chunks, onde cada um inicia obrigatoriamente com o cabeçalho Markdown original (`| Col1 | Col2 |` e `| --- | --- |`).

---

### Requirement: Subdivisão Recursiva com Overlap para Textos Longos (Camada 2)
O sistema DEVE subdividir recursivamente trechos de texto que excedam `chunk_size` (padrão 1000) respeitando `chunk_overlap` (padrão 150) e delimitadores naturais (parágrafos, linhas, períodos, espaços).

#### Scenario: Divisão recursiva com overlap
- **GIVEN** uma seção textual contendo 2500 caracteres
- **WHEN** `chunk_document` for chamado com `chunk_size = 1000` e `chunk_overlap = 150`
- **THEN** múltiplos sub-chunks devem ser gerados, respeitando o tamanho máximo e mantendo overlap textual entre sub-chunks adjacentes.

---

### Requirement: Injeção de Breadcrumb Contextual e Hash Criptográfico
O sistema DEVE injetar no início do campo `content` de cada chunk o cabeçalho contextual no formato `[Norma: {document_code} | Rev: {revision} | Seção: {section_code} - {section_title} | Pág: {page_number}]` e calcular o `chunk_hash` como o SHA-256 do conteúdo gerado.

#### Scenario: Validação de breadcrumb e idempotência do hash
- **GIVEN** um documento `DIS-NOR-030` revisão `07`
- **WHEN** os chunks forem gerados
- **THEN** todo chunk deve iniciar com o breadcrumb contextual padronizado e possuir `chunk_hash` idêntico ao SHA-256 de seu `content`.
