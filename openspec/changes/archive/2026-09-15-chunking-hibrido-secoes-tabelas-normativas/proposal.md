# Proposal: Chunking Híbrido Semântico Orientado a Seções e Tabelas Normativas

## Context
O assistente técnico Lumi (NeoGuide) processa documentos normativos extensos de distribuição de energia elétrica da Neoenergia (ex.: `DIS-NOR-030` com 140 páginas e `DIS-NOR-053` com 353 páginas). Após a etapa de parsing e sanitização (FEAT-01), o texto bruto higienizado contém títulos de seções hierárquicos, tabelas complexas em Markdown e delimitadores de página (`**[Página X]**`). A eficácia do motor de busca vetorial (pgvector) e a precisão da geração pelo LLM dependem diretamente da qualidade semântica da segmentação (chunking), assegurando rastreabilidade normativa exata, integridade de tabelas técnicas e contextualização por breadcrumb.

## Motivation & Value
A segmentação ingênua baseada unicamente em contagem de caracteres quebra tabelas técnicas ao meio, perde o vínculo com a seção ou capítulo normativo regulatório e mistura tópicos distintos em um mesmo embedding vetorial.
O chunking híbrido semântico introduzido nesta proposta oferece:
- **Preservação Estrutural (Camada 1)**: Particionamento orientado a seções regulatórias (`1.`, `5.2`, `6.7.16`, `Capítulo X`, `Anexo`) e blocos de tabelas Markdown.
- **Rastreabilidade Hierárquica e Marcadores de Página**: Rastreamento da pilha de seções ativas (`section_code`, `section_title`, `section_hierarchy`) e localização exata de páginas (`page_number`, `page_range` para spans multi-página).
- **Tratamento Especializado de Tabelas Técnicas**: Tabelas até ~2000 caracteres mantidas atômicas; tabelas gigantes divididas por linhas replicando compulsoriamente os cabeçalhos Markdown em cada sub-chunk gerado.
- **Subdivisão Recursiva com Overlap (Camada 2)**: Divisão de blocos de texto longos com `chunk_size=1000` e `chunk_overlap=150`, respeitando parágrafos e frases.
- **Injeção de Breadcrumb Contextual**: Cada chunk recebe no topo o cabeçalho padronizado `[Norma: {document_code} | Rev: {revision} | Seção: {section_code} - {section_title} | Pág: {page_number}]`, permitindo que os embeddings e o LLM compreendam imediatamente a qual norma e seção o trecho pertence.
- **Idempotência Criptográfica**: Geração de `chunk_hash` SHA-256 sobre o conteúdo completo do chunk, prevenindo duplicações no banco de dados vetorial.

## Scope

### In-Scope
- Modelo Pydantic `NormativeChunkData` em `src/lumi/ingestion/models.py`.
- Módulo `src/lumi/ingestion/chunker.py` com:
  - `parse_heading`: identificação e hierarquia de títulos normativos.
  - `recursive_split_text`: particionamento recursivo textual com overlap.
  - `chunk_table`: tratamento atômico e divisão lógica de tabelas com replicação de cabeçalhos.
  - `chunk_document`: orquestrador principal de particionamento semântico recebendo `ParsedDocument`.
- Exportação de `NormativeChunkData` e `chunk_document` em `src/lumi/ingestion/__init__.py`.
- Suíte exaustiva de testes unitários TDD em `tests/unit/test_chunker.py`.
- Sincronização da especificação canônica em `openspec/specs/document-ingestion/spec.md`.

### Out-of-Scope
- Geração de embeddings vetoriais via LLM/Gemini (escopo de indexação posterior).
- Persistência direta no PostgreSQL / pgvector.
