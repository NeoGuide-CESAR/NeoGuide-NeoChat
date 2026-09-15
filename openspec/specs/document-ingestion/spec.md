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
