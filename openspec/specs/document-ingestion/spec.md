# Spec: Ingestão, Higienização e Parsing de Documentos Normativos

## Requirements

### Requirement: Modelos Estruturados de Página e Documento Ingerido
O sistema DEVE representar páginas e documentos normativos através de modelos Pydantic v2 estritos (`DocumentPage` e `ParsedDocument`), garantindo a preservação do texto bruto, texto limpo, tabelas em formato Markdown e metadados de auditoria técnica.

#### Scenario: Instanciação de página de documento válida
- **GIVEN** número da página `1`, texto bruto contendo texto da norma e lista opcional de tabelas Markdown
- **WHEN** o modelo `DocumentPage` for instanciado
- **THEN** os atributos `page_number`, `raw_text`, `clean_text` e `tables` devem ser preservados e validados.

#### Scenario: Validação de número de página positivo
- **GIVEN** uma tentativa de criar `DocumentPage` com `page_number = 0` ou `page_number = -1`
- **WHEN** a validação do Pydantic for acionada
- **THEN** um erro de validação deve ser levantado rejeitando valores menores que 1.

#### Scenario: Instanciação de documento normativo parseado
- **GIVEN** código do documento `"DIS-NOR-030"`, título, revisão `"REV07"`, empresa `"Neoenergia Pernambuco"`, lista de páginas e arquivo de origem
- **WHEN** o modelo `ParsedDocument` for instanciado
- **THEN** os metadados e o texto consolidado `full_clean_text` devem estar acessíveis e estruturados.

---

### Requirement: Higienização Pura de Pontilhados de Sumário (TOC Dots)
O sistema DEVE fornecer a função `strip_toc_dots(text: str) -> str` capaz de remover linhas com sequências contínuas de pontos (`.....`) típicas de sumários normativos, mantendo o título do item e a numeração da página de destino sem introduzir ruídos vetoriais.

#### Scenario: Remoção de linha pontilhada mantendo item e página
- **GIVEN** a linha `"##### 1. CONTROLE DE ALTERAÇÕES ......................................................................................................................................................... 3"`
- **WHEN** a função `strip_toc_dots` for executada
- **THEN** a sequência de pontos deve ser removida ou condensada, preservando `"##### 1. CONTROLE DE ALTERAÇÕES 3"` de forma limpa.

---

### Requirement: Correção de Cabeçalhos Invertidos por OCR (Reverse OCR Table Headers)
O sistema DEVE fornecer a função `fix_reversed_table_headers(text: str) -> str` capaz de detectar e reverter tokens com letras espaçadas originários de orientação vertical em tabelas digitalizadas.

#### Scenario: Correção de termos de cabeçalho comuns em normas elétricas
- **GIVEN** um texto contendo `"|  | o ã s n e T | a iro g e ta C | a g ra C | a d a la ts n I | )W k ( | a d n a m e D | )A V k ( | )A ( ro tn u js iD |"`
- **WHEN** a função `fix_reversed_table_headers` for executada
- **THEN** os termos devem ser corrigidos para `"Tensão"`, `"Categoria"`, `"Carga"`, `"Instalada"`, `"(kW)"`, `"Demanda"`, `"(kVA)"` e `"Disjuntor (A)"` respectivamente.

#### Scenario: Correção de tensões e eletrodutos invertidos
- **GIVEN** um fragmento contendo `"V 7 2 1 / 0 2 2"`, `"o d a d il a n iF"`, `"s o tu d o rte lE"` e `"o tn e m a rre tA"`
- **WHEN** a função `fix_reversed_table_headers` for executada
- **THEN** os valores devem ser substituídos respectivamente por `"220 / 127 V"`, `"Finalidade"`, `"Eletrodutos"` e `"Aterramento"`.

---

### Requirement: Normalização de Espaços e Preservação de Grandezas Elétricas
O sistema DEVE fornecer a função `normalize_unicode_and_spaces(text: str) -> str` para padronizar caracteres e múltiplos espaços, garantindo a integridade exata de termos técnicos e grandezas de engenharia elétrica.

#### Scenario: Preservação de fases e grandezas de distribuição
- **GIVEN** um texto técnico contendo termos como `"3F"`, `"FN"`, `"FF"`, `"13,8 kV"`, `"380/220 V"`, `"75 kVA"`, `"15 kW"`, `"5 cv"` e `"50 m²"` com múltiplos espaços redundantes
- **WHEN** a função `normalize_unicode_and_spaces` for executada
- **THEN** os múltiplos espaços devem ser normalizados e todas as grandezas e fases devem ser preservadas integralmente.

---

### Requirement: Injeção de Marcadores de Página
O sistema DEVE fornecer a função `inject_page_markers(pages: list[DocumentPage]) -> str` para concatenar o conteúdo de múltiplas páginas inserindo o delimitador padronizado `**[Página X]**`.

#### Scenario: Concatenação com marcadores de página
- **GIVEN** uma lista contendo 2 objetos `DocumentPage` com números 1 e 2
- **WHEN** a função `inject_page_markers` for executada
- **THEN** a saída deve conter explicitamente `**[Página 1]**` antes do texto da primeira página e `**[Página 2]**` antes do texto da segunda página.

---

### Requirement: Parser de Documentos Markdown
O sistema DEVE fornecer a função `parse_markdown_file(file_path: Path | str) -> ParsedDocument` capaz de ler arquivos markdown de normas, identificar seções de página através do marcador `**[Página X]**`, extrair metadados e aplicar a higienização.

#### Scenario: Parsing de norma Markdown DIS-NOR-030
- **GIVEN** o arquivo normativo `docs/info/DIS-NOR-030-REV07.md`
- **WHEN** a função `parse_markdown_file` for executada
- **THEN** o objeto retornado deve possuir `document_code = "DIS-NOR-030"`, `revision = "07"` (ou `"REV07"`), conter dezenas de páginas particionadas e texto higienizado.

#### Scenario: Parsing de norma Markdown DIS-NOR-053
- **GIVEN** o arquivo normativo `docs/info/DIS-NOR-053-REV06.md`
- **WHEN** a função `parse_markdown_file` for executada
- **THEN** o objeto retornado deve possuir `document_code = "DIS-NOR-053"`, `revision = "06"` (ou `"REV06"`) e conter páginas indexadas a partir de 1.

---

### Requirement: Parser de Documentos PDF via pdfplumber
O sistema DEVE fornecer a função `parse_pdf_file(file_path: Path | str) -> ParsedDocument` para extrair texto e tabelas página a página a partir de arquivos PDF, convertendo as tabelas encontradas para formato Markdown.

#### Scenario: Extração de texto e tabela de arquivo PDF
- **GIVEN** um arquivo PDF contendo texto e uma tabela com linhas e colunas
- **WHEN** a função `parse_pdf_file` for executada
- **THEN** o objeto retornado deve conter cada página em `DocumentPage`, com o texto extraído, tabelas convertidas em Markdown tabular (`| col1 | col2 |`) e texto limpo.

---

### Requirement: Despachante Polimórfico de Ingestão (parse_document)
O sistema DEVE fornecer a função `parse_document(file_path: Path | str) -> ParsedDocument` que detecta a extensão do arquivo e direciona para o parser apropriado.

#### Scenario: Despacho para arquivo Markdown
- **GIVEN** um arquivo com extensão `.md`
- **WHEN** a função `parse_document` for chamada
- **THEN** deve invocar `parse_markdown_file` e retornar `ParsedDocument`.

#### Scenario: Despacho para arquivo PDF
- **GIVEN** um arquivo com extensão `.pdf`
- **WHEN** a função `parse_document` for chamada
- **THEN** deve invocar `parse_pdf_file` e retornar `ParsedDocument`.

#### Scenario: Rejeição de extensão não suportada
- **GIVEN** um arquivo com extensão não suportada (ex.: `.docx` ou `.txt`)
- **WHEN** a função `parse_document` for chamada
- **THEN** deve levantar `ValueError` informando extensão não suportada.

---

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
O sistema DEVE isolar tabelas Markdown em chunks dedicados com `metadata["is_table"] = True` e `metadata["table_id"]`. Tabelas de até ~2000 caracteres devem ser mantidas atômicas. Tabelas que excedam esse limite devem ser fracionadas logicamente por linhas com replicação obrigatória das linhas de cabeçalho Markdown em cada sub-chunk gerado.

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

