"""Parsers for technical normative documents in Markdown and PDF formats."""

import re
from collections.abc import Sequence
from pathlib import Path

import pdfplumber

from lumi.ingestion.models import DocumentPage, ParsedDocument
from lumi.ingestion.sanitizer import (
    fix_reversed_table_headers,
    inject_page_markers,
    normalize_unicode_and_spaces,
    strip_toc_dots,
)


def format_table_as_markdown(table_data: Sequence[Sequence[str | None]]) -> str:
    """Converte uma matriz de células extraída por pdfplumber em formato de tabela Markdown."""
    if not table_data:
        return ""

    cleaned_rows: list[list[str]] = []
    for row in table_data:
        if not row:
            continue
        cleaned_row = [(cell.replace("\n", " ").strip() if cell else "") for cell in row]
        if any(cleaned_row):
            cleaned_rows.append(cleaned_row)

    if not cleaned_rows:
        return ""

    num_cols = max(len(r) for r in cleaned_rows)
    normalized_rows = [r + [""] * (num_cols - len(r)) for r in cleaned_rows]

    header = normalized_rows[0]
    separator = ["---"] * num_cols
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in normalized_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def extract_markdown_tables(text: str) -> list[str]:
    """Localiza e extrai blocos de tabelas Markdown (| col1 | col2 |) no texto."""
    table_lines: list[str] = []
    tables: list[str] = []

    for line in text.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("|") and trimmed.endswith("|"):
            table_lines.append(line)
        else:
            if len(table_lines) >= 2:
                tables.append("\n".join(table_lines))
            table_lines = []

    if len(table_lines) >= 2:
        tables.append("\n".join(table_lines))

    return tables


def _sanitize_page_text(raw_text: str) -> str:
    """Aplica o pipeline completo de sanitização em texto de página."""
    return normalize_unicode_and_spaces(fix_reversed_table_headers(strip_toc_dots(raw_text)))


def _extract_markdown_metadata(content: str, file_name: str) -> tuple[str, str, str, str]:
    """Extrai document_code, title, revision e company a partir do cabeçalho Markdown."""
    # 1. Código do documento
    code_match = re.search(r"#\s*(DIS-NOR-\d+)", content)
    if not code_match:
        code_match = re.search(r"(DIS-NOR-\d+)", file_name, re.IGNORECASE)
    doc_code = code_match.group(1).upper() if code_match else "DIS-NOR-000"

    # 2. Título
    title_match = re.search(r"#\s*(?:DIS-NOR-\d+)?\s*[—\-–]\s*(.+)", content)
    if title_match:
        title = title_match.group(1).strip()
    else:
        first_line = content.strip().splitlines()[0] if content.strip() else file_name
        title = first_line.lstrip("#").strip()

    # 3. Revisão
    rev_match = re.search(r">\s*\*\*Revisão:\*\*\s*(\S+)", content)
    if not rev_match:
        rev_match = re.search(r"REV\s*[-_]?\s*(\d+)", file_name, re.IGNORECASE)
        revision = f"REV{rev_match.group(1)}" if rev_match else "REV01"
    else:
        revision = rev_match.group(1).strip()

    # 4. Empresa / Concessionária
    comp_match = re.search(r">\s*\*\*Empresa:\*\*\s*(.+)", content)
    company = comp_match.group(1).strip() if comp_match else "Neoenergia Pernambuco"

    return doc_code, title, revision, company


def parse_markdown_file(file_path: Path | str) -> ParsedDocument:
    """Lê um arquivo Markdown normativo, particiona por **[Página X]** e extrai metadados."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo Markdown não encontrado: {path}")

    content = path.read_text(encoding="utf-8")
    doc_code, title, revision, company = _extract_markdown_metadata(content, path.name)

    # Localização de marcadores **[Página X]**
    marker_pattern = re.compile(r"\*\*\[Página\s+(\d+)\]\*\*", re.IGNORECASE)
    matches = list(marker_pattern.finditer(content))

    pages: list[DocumentPage] = []

    if not matches:
        # Documento sem marcadores de página: trata como página única
        clean = _sanitize_page_text(content)
        tables = extract_markdown_tables(content)
        pages.append(DocumentPage(page_number=1, raw_text=content, clean_text=clean, tables=tables))
    else:
        for idx, match in enumerate(matches):
            page_num = int(match.group(1))
            start_pos = match.end()
            end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)

            page_raw = content[start_pos:end_pos].strip()
            page_clean = _sanitize_page_text(page_raw)
            tables = extract_markdown_tables(page_raw)

            pages.append(
                DocumentPage(
                    page_number=page_num,
                    raw_text=page_raw,
                    clean_text=page_clean,
                    tables=tables,
                )
            )

    full_clean_text = inject_page_markers(pages)

    return ParsedDocument(
        document_code=doc_code,
        title=title,
        revision=revision,
        company=company,
        pages=pages,
        full_clean_text=full_clean_text,
        source_file=str(path),
    )


def _extract_pdf_metadata(first_page_text: str, file_name: str) -> tuple[str, str, str, str]:
    """Infere metadados técnicos do PDF a partir da primeira página e nome do arquivo."""
    # Código
    code_match = re.search(r"(DIS-NOR-\d+)", first_page_text, re.IGNORECASE)
    if not code_match:
        code_match = re.search(r"(DIS-NOR-\d+)", file_name, re.IGNORECASE)
    doc_code = code_match.group(1).upper() if code_match else "DIS-NOR-000"

    # Revisão
    rev_match = re.search(r"REV\.?:\s*(\w+)", first_page_text, re.IGNORECASE)
    if not rev_match:
        rev_match = re.search(r"REV\s*[-_]?\s*(\d+)", file_name, re.IGNORECASE)
        revision = f"REV{rev_match.group(1)}" if rev_match else "REV01"
    else:
        revision = rev_match.group(1).strip()

    # Empresa
    company = "Neoenergia Pernambuco"
    if "Coelba" in first_page_text:
        company = "Neoenergia Coelba"
    elif "Cosern" in first_page_text:
        company = "Neoenergia Cosern"
    elif "Elektro" in first_page_text:
        company = "Neoenergia Elektro"

    # Título
    title_match = re.search(
        r"T[ÍI]TULO:\s*(?:CÓDIGO:\s*)?(.+?)(?:REV\.|APROV\.|Nº\s*PÁG)",
        first_page_text,
        re.DOTALL | re.IGNORECASE,
    )
    if title_match:
        raw_title = re.sub(r"\s+", " ", title_match.group(1))
        # Remove eventuais inserções do código da norma misturadas no cabeçalho
        clean_title = re.sub(r"DIS-NOR-\d+", "", raw_title).strip()
        title = clean_title or f"Norma Técnica {doc_code}"
    else:
        title = f"Norma Técnica {doc_code}"

    return doc_code, title, revision, company


def parse_pdf_file(file_path: Path | str) -> ParsedDocument:
    """Lê um arquivo PDF com pdfplumber, extrai texto e converte tabelas em Markdown por página."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {path}")

    pages: list[DocumentPage] = []
    first_page_text = ""

    with pdfplumber.open(path) as pdf:
        if not pdf.pages:
            raise ValueError(f"Arquivo PDF vazio ou sem páginas: {path}")

        first_page = pdf.pages[0]
        first_page_text = first_page.extract_text() or ""

        for idx, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text() or ""
            raw_tables = page.extract_tables() or []

            markdown_tables = [
                format_table_as_markdown(table) for table in raw_tables if table and any(table)
            ]

            clean_text = _sanitize_page_text(raw_text)

            pages.append(
                DocumentPage(
                    page_number=idx,
                    raw_text=raw_text,
                    clean_text=clean_text,
                    tables=markdown_tables,
                )
            )

    doc_code, title, revision, company = _extract_pdf_metadata(first_page_text, path.name)
    full_clean_text = inject_page_markers(pages)

    return ParsedDocument(
        document_code=doc_code,
        title=title,
        revision=revision,
        company=company,
        pages=pages,
        full_clean_text=full_clean_text,
        source_file=str(path),
    )


def parse_document(file_path: Path | str) -> ParsedDocument:
    """Ponto de entrada unificado que despacha conforme a extensão do arquivo (.md ou .pdf)."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    suffix = path.suffix.lower()
    if suffix == ".md":
        return parse_markdown_file(path)
    elif suffix == ".pdf":
        return parse_pdf_file(path)
    else:
        raise ValueError(
            f"Formato de arquivo não suportado: '{suffix}'. Utilize arquivos com extensão .md ou .pdf."
        )
