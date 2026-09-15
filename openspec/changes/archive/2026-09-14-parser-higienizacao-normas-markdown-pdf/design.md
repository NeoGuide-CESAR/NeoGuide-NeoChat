# Design: Arquitetura Modular de Ingestão, Sanitização e Parsing

## Context & Problem Statement
A extração de conhecimento normativo da Neoenergia (DIS-NOR-030 e DIS-NOR-053) requer um pipeline de ingestão robusto e desacoplado. As normas existem tanto em PDF original quanto em arquivos Markdown consolidados gerados por conversão OCR. Os documentos contêm tabelas críticas de dimensionamento elétrico, sumários com pontilhados excessivos e anomalias de OCR onde cabeçalhos aparecem invertidos com espaços intercalados (ex.: `o ã s n e T` em vez de `Tensão`).

É essencial estruturar os dados com metadados de rastreabilidade (código do documento, título, revisão, empresa, número da página) e preservar a exatidão das grandezas técnicas (tensão, corrente, potência, bitola de cabos, disjuntores).

## Architectural Overview

```
                  ┌─────────────────────────────────────────┐
                  │  parse_document(file_path: Path | str)  │
                  └────────────────────┬────────────────────┘
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
             [.md / Markdown]                     [.pdf / PDF]
                     │                                   │
                     ▼                                   ▼
           parse_markdown_file()               parse_pdf_file()
           - Split por **[Página X]**          - pdfplumber extract_text()
           - Extração de Header/Metadados       - extract_tables() -> Markdown
                     │                                   │
                     └─────────────────┬─────────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │     Pipeline de Sanitização   │
                       │ - strip_toc_dots              │
                       │ - fix_reversed_table_headers  │
                       │ - normalize_unicode_and_spaces│
                       │ - inject_page_markers         │
                       └───────────────┬───────────────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │   ParsedDocument (Pydantic)   │
                       │  - document_code: str         │
                       │  - title: str                 │
                       │  - revision: str              │
                       │  - company: str               │
                       │  - pages: list[DocumentPage]  │
                       │  - full_clean_text: str       │
                       │  - source_file: str           │
                       └───────────────────────────────┘
```

## Detailed Component Design

### 1. Modelos de Dados Pydantic (`src/lumi/ingestion/models.py`)
- `DocumentPage`:
  - `page_number: int` (validação `>= 1`)
  - `raw_text: str` (texto original extraído)
  - `clean_text: str` (texto após pipeline de sanitização)
  - `tables: list[str] = []` (tabelas extraídas da página em formato Markdown)
- `ParsedDocument`:
  - `document_code: str` (ex.: "DIS-NOR-030")
  - `title: str`
  - `revision: str` (ex.: "REV07" ou "07")
  - `company: str` (ex.: "Neoenergia Pernambuco")
  - `pages: list[DocumentPage]`
  - `full_clean_text: str` (texto integral higienizado com marcadores de página)
  - `source_file: str`

### 2. Funções Puras de Higienização (`src/lumi/ingestion/sanitizer.py`)
- `strip_toc_dots(text: str) -> str`:
  - Identifica e remove linhas ou fragmentos com sequências repetitivas de pontos (`\.{3,}` ou `(?:\.\s*){3,}`), preservando o número da página ou título associado.
- `fix_reversed_table_headers(text: str) -> str`:
  - Mapeia e corrige anomalias de OCR de palavras escritas ao contrário com caracteres espaçados.
  - Padrões conhecidos de tabelas da Neoenergia:
    - `o ã s n e T` / `o ã s n e t` -> `Tensão`
    - `a iro g e ta C` / `a iro g e t a C` -> `Categoria`
    - `)A ( ro tn u js iD` / `ro tn u js iD` / `) A ( ro tn u js iD` -> `Disjuntor (A)` / `Disjuntor`
    - `o d a d il a n iF` -> `Finalidade`
    - `a d a la ts n I` / `a d a la t s n I` -> `Instalada`
    - `a g ra C` -> `Carga`
    - `a d n a m e D` -> `Demanda`
    - `)W k (` / `) W k (` -> `(kW)`
    - `)A V k (` / `) A V k (` -> `(kVA)`
    - `o ã ç id e M` / `o ã ç i d e M` -> `Medição`
    - `s o tu d o rte lE` -> `Eletrodutos`
    - `o tu d o rte lE` -> `Eletroduto`
    - `s o m in íM` -> `Mínimos`
    - `o m in íM` -> `Mínimo`
    - `e s e s a F` / `s e s a F` -> `Fases`
    - `o rtu e N` -> `Neutro`
    - `o tn e m a rre tA` / `tn e m a rre tA` -> `Aterramento`
    - `V 7 2 1 / 0 2 2` -> `220 / 127 V`
    - `V 0 2 2 / 0 8 3` -> `380 / 220 V`
- `normalize_unicode_and_spaces(text: str) -> str`:
  - Aplica normalização Unicode `NFKC`.
  - Normaliza múltiplos espaços em branco horizontais (preservando quebras de linha essenciais).
  - Garante a integridade de grandezas técnicas como `3F`, `FN`, `FF`, `m²`, `kVA`, `kW`, `kV`, `cv`.
- `inject_page_markers(pages: list[DocumentPage]) -> str`:
  - Gera string consolidada unindo as páginas limpas delimitadas pelo cabeçalho `**[Página X]**`.

### 3. Extração e Parsers (`src/lumi/ingestion/parser.py`)
- `parse_markdown_file(file_path: Path | str) -> ParsedDocument`:
  - Lê o arquivo Markdown com encoding UTF-8.
  - Extrai metadados do cabeçalho (ex.: `# DIS-NOR-030 ...`, `Revisão: 07`, `Empresa: Neoenergia Pernambuco`).
  - Utiliza regex `\*\*\[Página\s+(\d+)\]\*\*` para particionar as páginas.
  - Sanitiza o texto de cada página e compõe a lista de `DocumentPage`.
- `parse_pdf_file(file_path: Path | str) -> ParsedDocument`:
  - Abre o PDF com `pdfplumber.open(file_path)`.
  - Itera sobre `pdf.pages`:
    - Extrai texto com `page.extract_text()`.
    - Extrai tabelas com `page.extract_tables()`.
    - Converte tabelas tabulares para formato Markdown padrão (`| col1 | col2 |`).
    - Higieniza e compõe `DocumentPage`.
  - Infere metadados do documento a partir do nome do arquivo ou da primeira página.
- `parse_document(file_path: Path | str) -> ParsedDocument`:
  - Avalia o sufixo (`.md` -> `parse_markdown_file`, `.pdf` -> `parse_pdf_file`).
  - Lança `ValueError` para extensões não suportadas.

## Error Handling & Edge Cases
- Arquivos inexistentes: lança `FileNotFoundError`.
- Documentos sem marcadores de página em Markdown: trata como documento de página única (`page_number=1`).
- Tabelas vazias ou nulas no PDF: ignora graciosamente sem quebrar a extração.
