"""Hybrid semantic chunker for normative technical documents (Neoenergia DIS-NOR-030 and DIS-NOR-053)."""

import re
from typing import Any

from lumi.ingestion.models import NormativeChunkData, ParsedDocument

PAGE_MARKER_REGEX = re.compile(r"\*\*\[Página\s+(\d+)\]\*\*", re.IGNORECASE)
TABLE_LINE_REGEX = re.compile(r"^\|.*\|\s*$")
TABLE_SEPARATOR_REGEX = re.compile(r"^\|(\s*:?-+:?\s*\|)+$")
TABLE_CAPTION_REGEX = re.compile(
    r"^(?:#{1,6}\s*)?(?:(Tabela|Quadro)\s+([A-Za-z0-9_.-]+))(?:\s*[-–—:]\s*(.*))?$",
    re.IGNORECASE,
)


def parse_heading(line: str) -> tuple[int, str | None, str] | None:
    """Identifica se uma linha corresponde a um título ou item normativo.

    Retorna uma tupla (nível_hierárquico, código_da_seção, título_da_seção) ou None.
    """
    trimmed = line.strip()
    if not trimmed:
        return None

    # Linhas de tabela não são títulos
    if trimmed.startswith("|") and trimmed.endswith("|"):
        return None

    # 1. Títulos Markdown (# a ######)
    hash_match = re.match(r"^(#{1,6})\s+(.*)$", trimmed)
    if hash_match:
        hashes = len(hash_match.group(1))
        content = hash_match.group(2).strip()

        # Verifica padrões especiais como Capítulo, Anexo ou Seção
        special_match = re.match(
            r"^((?:Capítulo|Capitulo|CAPÍTULO|Anexo|ANEXO|Seção|Secao|SEÇÃO)\s+[A-Za-z0-9IVXLCDM]+)\.?\s*[-–—.:]?\s*(.*)$",
            content,
            re.IGNORECASE,
        )
        if special_match:
            code = special_match.group(1).strip().rstrip(".")
            title = special_match.group(2).strip()
            return 1, code, title

        # Verifica código numérico no título Markdown (ex.: "1. CONTROLE", "5.2 Distribuidora")
        num_match = re.match(r"^(\d+(?:\.\d+)*)\.?\s*[-–—.:]?\s*(.*)$", content)
        if num_match:
            code = num_match.group(1).strip()
            title = num_match.group(2).strip()
            level = len(code.split("."))
            return level, code, title

        # Título Markdown sem código numérico (ex.: "### SUMÁRIO")
        return hashes, None, content

    # 2. Itens normativos em texto simples (sem hashes)
    special_match = re.match(
        r"^((?:Capítulo|Capitulo|CAPÍTULO|Anexo|ANEXO|Seção|Secao|SEÇÃO)\s+[A-Za-z0-9IVXLCDM]+)\.?\s*[-–—.:]?\s*(.*)$",
        trimmed,
        re.IGNORECASE,
    )
    if special_match:
        code = special_match.group(1).strip().rstrip(".")
        title = special_match.group(2).strip()
        return 1, code, title

    # Numeração com ao menos um ponto (ex.: "5.2 Distribuidoras", "6.7.16 Instalações")
    num_item_match = re.match(r"^(\d+\.\d+(?:\.\d+)*)\.?\s+([A-Za-zÀ-Ú0-9].*)$", trimmed)
    if num_item_match:
        code = num_item_match.group(1).strip()
        title = num_item_match.group(2).strip()
        level = len(code.split("."))
        return level, code, title

    return None


def format_breadcrumb(
    document_code: str,
    revision: str,
    section_code: str | None = None,
    section_title: str | None = None,
    page_number: int | None = None,
) -> str:
    """Gera o cabeçalho contextual (breadcrumb) padronizado no topo do chunk."""
    if section_code and section_title:
        section_display = f"{section_code} - {section_title}"
    elif section_code:
        section_display = section_code
    elif section_title:
        section_display = section_title
    else:
        section_display = "N/A"

    page_display = str(page_number) if page_number is not None else "N/A"

    return (
        f"[Norma: {document_code} | Rev: {revision} | "
        f"Seção: {section_display} | Pág: {page_display}]"
    )


def recursive_split_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    separators: list[str] | None = None,
) -> list[str]:
    """Divide recursivamente um texto longo em blocos menores com overlap."""
    if separators is None:
        separators = ["\n\n", "\n", ". ", "; ", " ", ""]

    stripped = text.strip()
    if not stripped:
        return []

    if len(stripped) <= chunk_size:
        return [stripped]

    chosen_sep = ""
    for sep in separators:
        if sep == "":
            chosen_sep = ""
            break
        if sep in stripped:
            chosen_sep = sep
            break

    if chosen_sep == "":
        step = max(1, chunk_size - chunk_overlap)
        slices = [stripped[i : i + chunk_size].strip() for i in range(0, len(stripped), step)]
        return [s for s in slices if s]

    splits = stripped.split(chosen_sep)
    next_separators = separators[separators.index(chosen_sep) + 1 :]

    chunks: list[str] = []
    current_pieces: list[str] = []
    current_len = 0
    sep_len = len(chosen_sep)

    for piece in splits:
        p_str = piece.strip()
        if not p_str and not current_pieces:
            continue

        piece_len = len(piece)
        if piece_len > chunk_size:
            sub_pieces = recursive_split_text(piece, chunk_size, chunk_overlap, next_separators)
            for sp in sub_pieces:
                if current_pieces:
                    chunks.append(chosen_sep.join(current_pieces).strip())
                    current_pieces = []
                    current_len = 0
                chunks.append(sp)
            continue

        projected_len = current_len + (sep_len if current_pieces else 0) + piece_len
        if projected_len <= chunk_size:
            current_pieces.append(piece)
            current_len = projected_len
        else:
            if current_pieces:
                chunks.append(chosen_sep.join(current_pieces).strip())
                # Calcula overlap a partir das últimas peças
                overlap_pieces: list[str] = []
                overlap_len = 0
                for op in reversed(current_pieces):
                    add_len = len(op) + (sep_len if overlap_pieces else 0)
                    if overlap_len + add_len <= chunk_overlap:
                        overlap_pieces.insert(0, op)
                        overlap_len += add_len
                    else:
                        break
                current_pieces = overlap_pieces + [piece]
                current_len = len(chosen_sep.join(current_pieces))
            else:
                current_pieces = [piece]
                current_len = piece_len

    if current_pieces:
        combined = chosen_sep.join(current_pieces).strip()
        if combined:
            chunks.append(combined)

    return [c for c in chunks if c]


def chunk_table(
    table_text: str,
    table_id: str,
    document_code: str,
    revision: str,
    section_code: str | None = None,
    section_title: str | None = None,
    page_number: int | None = None,
    page_range: list[int] | None = None,
    metadata: dict[str, Any] | None = None,
    max_table_chars: int = 2000,
) -> list[NormativeChunkData]:
    """Segmenta tabelas Markdown mantendo atomicidade ou replicando cabeçalhos em tabelas gigantes."""
    clean_table = table_text.strip()
    if not clean_table:
        return []

    lines = [line for line in clean_table.splitlines() if line.strip()]
    if not lines:
        return []

    base_metadata: dict[str, Any] = dict(metadata or {})
    base_metadata["is_table"] = True
    base_metadata["table_id"] = table_id
    if page_range and len(page_range) == 2 and page_range[0] != page_range[1]:
        base_metadata["page_range"] = page_range

    breadcrumb = format_breadcrumb(
        document_code=document_code,
        revision=revision,
        section_code=section_code,
        section_title=section_title,
        page_number=page_number,
    )

    # 1. Tabela atômica (menor ou igual ao limite de caracteres)
    if len(clean_table) <= max_table_chars:
        content = f"{breadcrumb}\n\n{clean_table}"
        return [
            NormativeChunkData(
                document_code=document_code,
                revision=revision,
                content=content,
                section_code=section_code,
                section_title=section_title,
                page_number=page_number,
                metadata=base_metadata,
            )
        ]

    # 2. Tabela gigante: fracionamento com replicação obrigatória de cabeçalhos
    sep_idx = -1
    for idx, line in enumerate(lines):
        if TABLE_SEPARATOR_REGEX.match(line.strip()):
            sep_idx = idx
            break

    if sep_idx != -1:
        header_lines = lines[: sep_idx + 1]
        data_rows = lines[sep_idx + 1 :]
    else:
        header_lines = lines[:1]
        data_rows = lines[1:]

    header_block = "\n".join(header_lines)
    header_len = len(header_block)

    sub_table_blocks: list[str] = []
    current_rows: list[str] = []
    current_len = header_len

    for row in data_rows:
        row_len = len(row) + 1  # newline
        if current_rows and (current_len + row_len > max_table_chars):
            sub_table_blocks.append(header_block + "\n" + "\n".join(current_rows))
            current_rows = [row]
            current_len = header_len + row_len
        else:
            current_rows.append(row)
            current_len += row_len

    if current_rows:
        sub_table_blocks.append(header_block + "\n" + "\n".join(current_rows))

    total_parts = len(sub_table_blocks)
    result_chunks: list[NormativeChunkData] = []

    for part_idx, sub_table in enumerate(sub_table_blocks, start=1):
        chunk_meta = dict(base_metadata)
        chunk_meta["table_part"] = part_idx
        chunk_meta["total_parts"] = total_parts

        content = f"{breadcrumb}\n\n{sub_table}"
        result_chunks.append(
            NormativeChunkData(
                document_code=document_code,
                revision=revision,
                content=content,
                section_code=section_code,
                section_title=section_title,
                page_number=page_number,
                metadata=chunk_meta,
            )
        )

    return result_chunks


def chunk_document(
    document: ParsedDocument,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    max_table_chars: int = 2000,
) -> list[NormativeChunkData]:
    """Realiza o chunking híbrido semântico orientado a seções e tabelas de uma norma técnica."""
    if chunk_size <= 0:
        raise ValueError("chunk_size deve ser maior que zero")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap não pode ser negativo")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap deve ser menor que chunk_size")

    full_text = document.full_clean_text.strip()
    if not full_text:
        return []

    lines = document.full_clean_text.splitlines()

    current_page: int | None = None
    section_stack: list[tuple[int, str | None, str]] = []

    active_text_lines: list[str] = []
    active_table_lines: list[str] = []
    active_pages: set[int] = set()

    table_counter = 0
    all_chunks: list[NormativeChunkData] = []

    def get_current_section() -> tuple[str | None, str | None, list[str]]:
        if not section_stack:
            return None, None, []
        leaf_code, leaf_title = section_stack[-1][1], section_stack[-1][2]
        hierarchy = [f"{s[1]} - {s[2]}" if s[1] and s[2] else (s[1] or s[2]) for s in section_stack]
        return leaf_code, leaf_title, hierarchy

    def flush_text_block() -> None:
        nonlocal active_text_lines, active_pages
        if not active_text_lines:
            return

        text_block = "\n".join(active_text_lines).strip()
        active_text_lines = []

        if not text_block:
            active_pages = set([current_page]) if current_page is not None else set()
            return

        sec_code, sec_title, sec_hierarchy = get_current_section()

        page_num: int | None = None
        page_range: list[int] | None = None
        if active_pages:
            sorted_pages = sorted(active_pages)
            page_num = sorted_pages[0]
            if sorted_pages[0] != sorted_pages[-1]:
                page_range = [sorted_pages[0], sorted_pages[-1]]

        breadcrumb = format_breadcrumb(
            document_code=document.document_code,
            revision=document.revision,
            section_code=sec_code,
            section_title=sec_title,
            page_number=page_num,
        )

        meta: dict[str, Any] = {"is_table": False}
        if sec_hierarchy:
            meta["section_hierarchy"] = sec_hierarchy
        if page_range:
            meta["page_range"] = page_range

        if len(text_block) <= chunk_size:
            content = f"{breadcrumb}\n\n{text_block}"
            all_chunks.append(
                NormativeChunkData(
                    document_code=document.document_code,
                    revision=document.revision,
                    content=content,
                    section_code=sec_code,
                    section_title=sec_title,
                    page_number=page_num,
                    metadata=dict(meta),
                )
            )
        else:
            pieces = recursive_split_text(text_block, chunk_size, chunk_overlap)
            for piece in pieces:
                content = f"{breadcrumb}\n\n{piece}"
                all_chunks.append(
                    NormativeChunkData(
                        document_code=document.document_code,
                        revision=document.revision,
                        content=content,
                        section_code=sec_code,
                        section_title=sec_title,
                        page_number=page_num,
                        metadata=dict(meta),
                    )
                )

        # Reseta as páginas ativas para a página corrente
        active_pages = set([current_page]) if current_page is not None else set()

    def flush_table_block(table_caption: str | None = None) -> None:
        nonlocal active_table_lines, table_counter, active_pages
        if not active_table_lines:
            return

        table_str = "\n".join(active_table_lines).strip()
        active_table_lines = []

        if not table_str:
            return

        table_counter += 1
        table_id = f"table_{table_counter}"

        # Tenta extrair id e legenda da tabela a partir de caption ou do contexto
        if table_caption:
            cap_match = TABLE_CAPTION_REGEX.match(table_caption)
            if cap_match:
                tipo = cap_match.group(1).lower()
                num = cap_match.group(2).lower()
                table_id = f"{tipo}_{num}"
            table_str = f"{table_caption}\n{table_str}"

        sec_code, sec_title, sec_hierarchy = get_current_section()

        page_num: int | None = None
        page_range: list[int] | None = None
        if active_pages:
            sorted_pages = sorted(active_pages)
            page_num = sorted_pages[0]
            if sorted_pages[0] != sorted_pages[-1]:
                page_range = [sorted_pages[0], sorted_pages[-1]]

        table_meta: dict[str, Any] = {}
        if sec_hierarchy:
            table_meta["section_hierarchy"] = sec_hierarchy

        table_chunks = chunk_table(
            table_text=table_str,
            table_id=table_id,
            document_code=document.document_code,
            revision=document.revision,
            section_code=sec_code,
            section_title=sec_title,
            page_number=page_num,
            page_range=page_range,
            metadata=table_meta,
            max_table_chars=max_table_chars,
        )
        all_chunks.extend(table_chunks)
        active_pages = set([current_page]) if current_page is not None else set()

    for line in lines:
        trimmed = line.strip()

        # Detecção de marcadores de página
        page_match = PAGE_MARKER_REGEX.search(line)
        if page_match:
            current_page = int(page_match.group(1))
            active_pages.add(current_page)
            # Remove o marcador da linha
            line = PAGE_MARKER_REGEX.sub("", line)
            trimmed = line.strip()
            if not trimmed:
                continue

        # Detecção de linhas de tabela
        if TABLE_LINE_REGEX.match(trimmed):
            if active_text_lines:
                # Verifica se a última linha de texto acumulada era uma legenda de tabela
                possible_caption = None
                last_line = active_text_lines[-1].strip()
                if TABLE_CAPTION_REGEX.match(last_line):
                    possible_caption = active_text_lines.pop().strip()
                flush_text_block()
                if possible_caption:
                    active_table_lines.append(possible_caption)

            active_table_lines.append(line)
            continue

        # Se estávamos em uma tabela e a linha não é mais tabela
        if active_table_lines:
            flush_table_block()

        # Detecção de títulos e itens normativos
        heading_info = parse_heading(line)
        if heading_info is not None:
            # Novo item normativo encontrado: descarrega o bloco textual anterior
            flush_text_block()

            level, code, title = heading_info
            # Atualiza pilha de seções
            while section_stack and section_stack[-1][0] >= level:
                section_stack.pop()
            section_stack.append((level, code, title))

            active_text_lines.append(line)
            continue

        # Linha regular de texto
        active_text_lines.append(line)

    # Finalização do documento
    if active_table_lines:
        flush_table_block()
    if active_text_lines:
        flush_text_block()

    return all_chunks
