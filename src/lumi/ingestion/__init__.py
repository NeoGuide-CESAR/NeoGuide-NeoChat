"""Ingestion package for normative documents (Markdown and PDF)."""

from lumi.ingestion.chunker import (
    chunk_document,
    chunk_table,
    format_breadcrumb,
    parse_heading,
    recursive_split_text,
)
from lumi.ingestion.models import DocumentPage, NormativeChunkData, ParsedDocument
from lumi.ingestion.parser import (
    extract_markdown_tables,
    format_table_as_markdown,
    parse_document,
    parse_markdown_file,
    parse_pdf_file,
)
from lumi.ingestion.pipeline import (
    IngestionResult,
    generate_embeddings_with_retry,
    ingest_normative_file,
)
from lumi.ingestion.sanitizer import (
    fix_reversed_table_headers,
    inject_page_markers,
    normalize_unicode_and_spaces,
    strip_toc_dots,
)

__all__ = [
    "DocumentPage",
    "IngestionResult",
    "NormativeChunkData",
    "ParsedDocument",
    "chunk_document",
    "chunk_table",
    "extract_markdown_tables",
    "fix_reversed_table_headers",
    "format_breadcrumb",
    "format_table_as_markdown",
    "generate_embeddings_with_retry",
    "ingest_normative_file",
    "inject_page_markers",
    "normalize_unicode_and_spaces",
    "parse_document",
    "parse_heading",
    "parse_markdown_file",
    "parse_pdf_file",
    "recursive_split_text",
    "strip_toc_dots",
]
