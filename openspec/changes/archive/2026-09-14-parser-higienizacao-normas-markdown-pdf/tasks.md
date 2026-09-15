# Tasks: Implementação do Parser e Higienização de Normas Técnicas

- [x] 1. Configuração de dependências <!-- id: 1-dependencies -->
    - [x] 1.1 Adicionar `pdfplumber>=0.11.0` nas dependências do `pyproject.toml` <!-- id: 1.1-pdfplumber -->
    - [x] 1.2 Executar `uv sync` ou verificar resolução de pacotes <!-- id: 1.2-sync -->

- [x] 2. Definição dos Modelos de Ingestão <!-- id: 2-models -->
    - [x] 2.1 Criar pacote `src/lumi/ingestion/__init__.py` <!-- id: 2.1-pkg-init -->
    - [x] 2.2 Criar modelos Pydantic v2 `DocumentPage` e `ParsedDocument` em `src/lumi/ingestion/models.py` <!-- id: 2.2-pydantic-models -->

- [x] 3. Implementação das Funções Puras de Higienização <!-- id: 3-sanitizer -->
    - [x] 3.1 Implementar `strip_toc_dots` para sumários em `src/lumi/ingestion/sanitizer.py` <!-- id: 3.1-strip-toc -->
    - [x] 3.2 Implementar `fix_reversed_table_headers` com dicionário e padrões de OCR reverso <!-- id: 3.2-reversed-headers -->
    - [x] 3.3 Implementar `normalize_unicode_and_spaces` preservando grandezas técnicas <!-- id: 3.3-normalize-spaces -->
    - [x] 3.4 Implementar `inject_page_markers` para concatenação com delimitadores <!-- id: 3.4-inject-markers -->

- [x] 4. Implementação dos Parsers de Documento <!-- id: 4-parsers -->
    - [x] 4.1 Implementar `parse_markdown_file` em `src/lumi/ingestion/parser.py` <!-- id: 4.1-parse-md -->
    - [x] 4.2 Implementar `parse_pdf_file` com extração de tabelas formatadas em Markdown <!-- id: 4.2-parse-pdf -->
    - [x] 4.3 Implementar despachante `parse_document` baseado na extensão de arquivo <!-- id: 4.3-parse-doc -->

- [x] 5. Testes Unitários Abrangentes <!-- id: 5-tests -->
    - [x] 5.1 Criar `tests/unit/test_parser.py` com testes para todas as funções de `sanitizer.py` <!-- id: 5.1-test-sanitizer -->
    - [x] 5.2 Implementar testes de parser Markdown com arquivos reais `DIS-NOR-030-REV07.md` e `DIS-NOR-053-REV06.md` <!-- id: 5.2-test-md -->
    - [x] 5.3 Implementar testes de parser PDF sintético/mockado <!-- id: 5.3-test-pdf -->
    - [x] 5.4 Testar validação de grandezas elétricas e integridade de tipos <!-- id: 5.4-test-units -->
    - [x] 5.5 Executar `uv run --extra dev pytest tests/unit/test_parser.py` e garantir 100% de sucesso <!-- id: 5.5-run-pytest -->

- [x] 6. Sincronização e Arquivamento OpenSpec <!-- id: 6-openspec -->
    - [x] 6.1 Sincronizar delta specs para `openspec/specs/document-ingestion/spec.md` <!-- id: 6.1-sync-specs -->
    - [x] 6.2 Arquivar change em `openspec/changes/archive/2026-09-14-parser-higienizacao-normas-markdown-pdf/` <!-- id: 6.2-archive -->
    - [x] 6.3 Realizar commit limpo `feat(FEAT-01): parser e higienizacao de documentos normativos Markdown e PDF` <!-- id: 6.3-commit -->
