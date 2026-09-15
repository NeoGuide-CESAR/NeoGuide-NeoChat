# Proposal: Parser e Higienização de Normas Técnicas (Markdown e PDF)

## Context
O Lumi (NeoGuide) é o assistente normativo inteligente para engenharia de distribuição e infraestrutura de redes elétricas da Neoenergia (com foco principal nas normas DIS-NOR-030 e DIS-NOR-053 da Neoenergia Pernambuco, Coelba, Cosern e Elektro). 
Os documentos normativos são compostos por dezenas a centenas de páginas em formato PDF ou transcrições estruturadas em Markdown, contendo textos regulatórios, tabelas de dimensionamento de padrão de entrada, disjuntores, ramais aéreos/subterrâneos e grandezas elétricas críticas.

Em documentos gerados via OCR ou convertidos a partir de editorações antigas em PDF/Markdown, ocorrem anomalias textuais severas:
1. Cabeçalhos de tabelas invertidos caractere a caractere ou palavra por palavra (ex.: `o ã s n e T` para Tensão, `a iro g e ta C` para Categoria, `)A ( ro tn u js iD` para Disjuntor (A), `o d a d il a n iF` para Finalidade, `o ã ç id e M` para Medição, etc.).
2. Sumários e índices com linhas repletas de pontilhados contínuos (`..... 5`), gerando ruído nos embeddings vetoriais.
3. Inconsistências de espaçamento e normalização de caracteres Unicode que podem descaracterizar grandezas de engenharia elétrica fundamentais como `3F`, `FN`, `FF`, `m²`, `kVA`, `kW`, `kV`, `cv`.
4. Ausência de marcadores explícitos de fronteira de página para suportar a rastreabilidade e citação obrigatória por página (`[Página X]`).

## Motivation & Value
A ingestão de alta precisão é o alicerce indispensável para toda a pipeline de RAG (Retrieval-Augmented Generation). Se o texto indexado contém cabeçalhos corrompidos por OCR ou carece de numeração precisa de página, a busca vetorial e a LLM falharão ao responder perguntas técnicas ou apontar a página correta da norma:
1. **Sanitização Determinística e Pura:** Garante reparação de artefatos de OCR e sumários sem perda de dados semânticos nem dependência de chamadas lentas de IA.
2. **Preservação Fiel de Grandezas de Engenharia:** Protege símbolos como fases (`3F`, `FN`, `FF`), unidades de potência e tensão (`kVA`, `kW`, `kV`, `cv`), áreas (`m²`) e separadores decimais (`5,1 - 10`).
3. **Suporte Dual a Markdown e PDF:** Permite tanto o processamento direto de arquivos markdown pré-compilados (`DIS-NOR-030-REV07.md`, `DIS-NOR-053-REV06.md`) quanto a extração direta de PDFs originais via `pdfplumber` com extração e formatação de tabelas estruturadas em Markdown.
4. **Rastreabilidade Fina por Página:** Cada página do documento é encapsulada em um modelo Pydantic `DocumentPage` com preservação do texto original (`raw_text`), texto limpo (`clean_text`), tabelas extraídas e injeção do marcador de página `**[Página X]**`.

## Scope

### In-Scope
- Dependência `pdfplumber>=0.11.0` adicionada a `pyproject.toml`.
- Módulo `src/lumi/ingestion/__init__.py` expondo os componentes de ingestão.
- Modelos Pydantic v2 em `src/lumi/ingestion/models.py`:
  - `DocumentPage`: número da página, texto bruto, texto higienizado e lista de tabelas formatadas em Markdown.
  - `ParsedDocument`: código normativo, título, revisão, concessionária/empresa, páginas, texto consolidado e caminho do arquivo de origem.
- Módulo de higienização funcional pura em `src/lumi/ingestion/sanitizer.py`:
  - `strip_toc_dots(text: str) -> str`: remove sequências de pontilhados de sumário mantendo o número da página.
  - `fix_reversed_table_headers(text: str) -> str`: repara strings com caracteres ou tokens invertidos de cabeçalhos de tabela OCR.
  - `normalize_unicode_and_spaces(text: str) -> str`: normaliza quebras de linha e espaços múltiplos preservando símbolos e grandezas elétricas.
  - `inject_page_markers(pages: list[DocumentPage]) -> str`: concatena o texto consolidado delimitando claramente as páginas com `**[Página X]**`.
- Módulo de parsing em `src/lumi/ingestion/parser.py`:
  - `parse_markdown_file(file_path: Path | str) -> ParsedDocument`: analisa Markdowns normativos com metadados de cabeçalho e delimitadores `**[Página X]**`.
  - `parse_pdf_file(file_path: Path | str) -> ParsedDocument`: extrai texto e tabelas página a página via `pdfplumber`, convertendo tabelas para Markdown.
  - `parse_document(file_path: Path | str) -> ParsedDocument`: despachante polimórfico baseado na extensão do arquivo.
- Testes unitários abrangentes em `tests/unit/test_parser.py` cobrindo todas as funções do sanitizer, extração dos documentos reais de `docs/info/`, mock/sintético de PDF e integridade de grandezas normativas.

### Out-of-Scope
- Chunking e geração de embeddings com divisão por janelas deslizantes (escopo de task subsequente de indexação vetorial).
- Persistência direta no PostgreSQL/pgvector.
- Processamento de imagens rasterizadas com Tesseract / EasyOCR (foco em PDF nativo/vetorial e Markdown já digitalizado).
