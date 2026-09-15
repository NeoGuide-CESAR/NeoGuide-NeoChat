"""Ingestion package for normative documents (Markdown and PDF)."""

from lumi.ingestion.models import DocumentPage, ParsedDocument
from lumi.ingestion.parser import (
    extract_markdown_tables,
    format_table_as_markdown,
    parse_document,
    parse_markdown_file,
    parse_pdf_file,
)
from lumi.ingestion.sanitizer import (
    fix_reversed_table_headers,
    inject_page_markers,
    normalize_unicode_and_spaces,
    strip_toc_dots,
)

__all__ = [
    "DocumentPage",
    "ParsedDocument",
    "extract_markdown_tables",
    "fix_reversed_table_headers",
    "format_table_as_markdown",
    "inject_page_markers",
    "normalize_unicode_and_spaces",
    "parse_document",
    "parse_markdown_file",
    "parse_pdf_file",
    "strip_toc_dots",
]
