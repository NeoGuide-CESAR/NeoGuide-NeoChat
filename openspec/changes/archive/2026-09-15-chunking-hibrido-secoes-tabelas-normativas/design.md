# Design: Chunking Híbrido Semântico Orientado a Seções e Tabelas Normativas

## Technical Decisions

### 1. Modelo de Dados Pydantic v2: `NormativeChunkData`
- Modelo imutável (`ConfigDict(frozen=True)`) com os atributos estritos:
  - `document_code: str`: código da norma (ex.: `'DIS-NOR-030'`, `'DIS-NOR-053'`).
  - `revision: str`: revisão (ex.: `'07'`, `'REV07'`).
  - `content: str`: texto íntegro do chunk com breadcrumb contextual no cabeçalho.
  - `section_code: str | None = None`: código da seção normativa ativa (ex.: `'5.2'`, `'6.7.16'`).
  - `section_title: str | None = None`: título da seção ativa (ex.: `'Distribuidoras Nordeste'`).
  - `page_number: int | None = None`: página de início (com validação `ge=1`).
  - `metadata: dict[str, Any] = Field(default_factory=dict)`: metadados com `is_table: bool`, `table_id: str | None`, `page_range: list[int]` (para blocos multi-página), `section_hierarchy: list[str]`.
  - `chunk_hash: str`: hash SHA-256 computado sobre `content`, preenchido automaticamente caso não fornecido para garantir idempotência de ingestão.

### 2. Particionamento Semântico Estrutural (Camada 1)
- Identificação de títulos e itens normativos via `parse_heading(line: str) -> tuple[int, str | None, str] | None`:
  - Detecta padrões com ou sem marcadores de nível Markdown (`#`, `##`, `###`, `####`, `#####`).
  - Interpreta numerações normativas (`1.`, `5.2`, `6.7.16`, `6.1.1.1`), capítulos (`Capítulo X`) e anexos (`Anexo III`).
  - Mantém uma pilha dinâmica hierárquica `section_stack`: ao identificar um item de nível $d$, elementos de nível $\ge d$ são removidos, preservando a cadeia de seções pai-filho.
- Detecção contínua de marcadores `**[Página X]**`:
  - Rastreia a página corrente e o conjunto de páginas tocadas por cada bloco.
  - Se o bloco abranger mais de uma página, preenche `metadata["page_range"] = [min_pag, max_pag]`.
  - O marcador artificial `**[Página X]**` é absorvido para rastreamento de páginas e não polui o texto dos blocos.

### 3. Tratamento Especializado de Tabelas Markdown
- Identificação de blocos de tabela através de linhas delimitadas por `|`.
- Threshold de atomicidade: tabelas com até ~2000 caracteres permanecem 100% atômicas (`metadata["is_table"] = True`, `metadata["table_id"] = ...`).
- Tabelas gigantes (> 2000 caracteres):
  - Detecção da linha de cabeçalho e do separador Markdown (`| --- | --- |`).
  - Divisão lógica das linhas de dados em fatias que respeitam o limite de tamanho.
  - **Replicação obrigatória** das linhas de cabeçalho Markdown da tabela no início de cada sub-chunk gerado.
  - Preservação do `table_id` e atribuição de `table_part` e `total_parts`.

### 4. Subdivisão Recursiva com Overlap para Textos Longos (Camada 2)
- Trechos textuais pertencentes a uma seção que excedam `chunk_size` (padrão 1000) sofrem divisão recursiva com `chunk_overlap` (padrão 150).
- Ordem de separadores: quebras de parágrafo (`\n\n`), quebras de linha (`\n`), finais de período (`. `, `; `), espaços (` `) e caracteres individuais.
- Garante que itens de listas e orações técnicas não sejam cortados abruptamente.

### 5. Injeção Contextual de Breadcrumb
- No topo de cada chunk gerado, insere o cabeçalho contextual:
  `[Norma: {document_code} | Rev: {revision} | Seção: {section_display} | Pág: {page_display}]`
  - Seção formatada como `{section_code} - {section_title}` ou `{section_code}` ou `{section_title}` ou `'N/A'`.
  - Página formatada com `page_number` ou `'N/A'`.
- Separação clara entre o breadcrumb contextual e o corpo do texto por linha em branco (`\n\n`).
