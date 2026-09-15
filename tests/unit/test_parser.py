"""Unit tests for technical normative document ingestion, sanitization, and parsing."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

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

# Paths para os documentos reais presentes no repositório
DOCS_INFO_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "info"
DIS_NOR_030_MD = DOCS_INFO_DIR / "DIS-NOR-030-REV07.md"
DIS_NOR_053_MD = DOCS_INFO_DIR / "DIS-NOR-053-REV06.md"
DIS_NOR_030_PDF = DOCS_INFO_DIR / "DIS-NOR-030-REV07.pdf"


# ==============================================================================
# Testes do Sanitizer
# ==============================================================================


class TestSanitizer:
    """Suíte de testes para as funções puras de sanitização."""

    def test_strip_toc_dots_removes_dots_and_preserves_page_numbers(self) -> None:
        raw_toc = (
            "##### 1. CONTROLE DE ALTERAÇÕES .................................................................... 3\n"
            "##### 2. DOCUMENTOS ANTECESSORES ................................................................ 4\n"
            "..... 5\n"
            "........................................\n"
            "Item sem pontos 10"
        )
        cleaned = strip_toc_dots(raw_toc)
        assert "##### 1. CONTROLE DE ALTERAÇÕES 3" in cleaned
        assert "##### 2. DOCUMENTOS ANTECESSORES 4" in cleaned
        assert "5" in cleaned
        assert "Item sem pontos 10" in cleaned
        assert "....." not in cleaned

    def test_strip_toc_dots_empty_input(self) -> None:
        assert strip_toc_dots("") == ""

    def test_fix_reversed_table_headers_replaces_ocr_anomalies(self) -> None:
        corrupted_header = (
            "|  | o ã s n e T | a iro g e ta C | a g ra C | a d a la ts n I | "
            ")W k ( | a d n a m e D | )A V k ( | )A ( ro tn u js iD | "
            "o d a d il a n iF | o ã ç id e M | s o tu d o rte lE | s o m in íM | "
            "e s e s a F | o rtu e N | o tu d o rte lE | o m in íM | o tn e m a rre tA |"
        )
        corrected = fix_reversed_table_headers(corrupted_header)

        assert "Tensão" in corrected
        assert "Categoria" in corrected
        assert "Carga" in corrected
        assert "Instalada" in corrected
        assert "(kW)" in corrected
        assert "Demanda" in corrected
        assert "(kVA)" in corrected
        assert "Disjuntor (A)" in corrected
        assert "Finalidade" in corrected
        assert "Medição" in corrected
        assert "Eletrodutos" in corrected
        assert "Mínimos" in corrected
        assert "Fases" in corrected
        assert "Neutro" in corrected
        assert "Eletroduto" in corrected
        assert "Mínimo" in corrected
        assert "Aterramento" in corrected

    def test_fix_reversed_table_headers_voltage_and_complex_phrases(self) -> None:
        phrase = "| V 7 2 1 / 0 2 2 | o t n e m ic e n ro F e d o ã s n e T | )W k ( a d a la t s n I a g ra C |"
        corrected = fix_reversed_table_headers(phrase)
        assert "220 / 127 V" in corrected
        assert "Tensão de Fornecimento" in corrected
        assert "Carga Instalada (kW)" in corrected

    def test_fix_reversed_table_headers_empty_and_normal_text(self) -> None:
        assert fix_reversed_table_headers("") == ""
        normal_text = "Texto comum sem artefatos de OCR"
        assert fix_reversed_table_headers(normal_text) == normal_text

    def test_normalize_unicode_and_spaces_preserves_electrical_units(self) -> None:
        electrical_snippet = (
            "Fornecimento em 3F   e   FN ou FF com tensão de 13,8 kV ou 380/220 V.\n"
            "Potência instalada de    75 kVA e demanda de 15 kW para motores de 5 cv.\n"
            "Área mínima de 50 m² com cabos de bitola 5,1 - 10 mm².\n\n\n\n"
            "Fim do trecho."
        )
        normalized = normalize_unicode_and_spaces(electrical_snippet)

        # Verificação da integridade das grandezas
        assert "3F" in normalized
        assert "FN" in normalized
        assert "FF" in normalized
        assert "13,8 kV" in normalized
        assert "380/220 V" in normalized
        assert "75 kVA" in normalized
        assert "15 kW" in normalized
        assert "5 cv" in normalized
        assert "m²" in normalized
        assert "5,1 - 10" in normalized

        # Verificação de colapso de espaços e quebras excessivas
        assert "   " not in normalized
        assert "\n\n\n" not in normalized

    def test_normalize_unicode_and_spaces_empty_input(self) -> None:
        assert normalize_unicode_and_spaces("") == ""

    def test_inject_page_markers(self) -> None:
        p1 = DocumentPage(
            page_number=1, raw_text="Texto bruto 1", clean_text="Texto limpo página 1"
        )
        p2 = DocumentPage(
            page_number=2, raw_text="Texto bruto 2", clean_text="Texto limpo página 2"
        )
        p3 = DocumentPage(page_number=3, raw_text="", clean_text="")

        output = inject_page_markers([p1, p2, p3])
        assert "**[Página 1]**\n\nTexto limpo página 1" in output
        assert "**[Página 2]**\n\nTexto limpo página 2" in output
        assert "**[Página 3]**" in output


# ==============================================================================
# Testes dos Modelos Pydantic v2
# ==============================================================================


class TestModels:
    """Suíte de testes para os modelos Pydantic DocumentPage e ParsedDocument."""

    def test_document_page_valid(self) -> None:
        page = DocumentPage(
            page_number=1,
            raw_text="Raw",
            clean_text="Clean",
            tables=["| Col1 | Col2 |\n| --- | --- |\n| A | B |"],
        )
        assert page.page_number == 1
        assert page.raw_text == "Raw"
        assert page.clean_text == "Clean"
        assert len(page.tables) == 1

    def test_document_page_rejects_zero_or_negative_page_number(self) -> None:
        with pytest.raises(ValidationError):
            DocumentPage(page_number=0, raw_text="R", clean_text="C")

        with pytest.raises(ValidationError):
            DocumentPage(page_number=-5, raw_text="R", clean_text="C")

    def test_document_page_immutability(self) -> None:
        page = DocumentPage(page_number=1, raw_text="R", clean_text="C")
        with pytest.raises(ValidationError):
            # Objeto frozen não permite atribuição
            page.page_number = 2  # type: ignore[misc]

    def test_parsed_document_valid(self) -> None:
        p = DocumentPage(page_number=1, raw_text="R", clean_text="C")
        doc = ParsedDocument(
            document_code="DIS-NOR-030",
            title="Fornecimento de Energia",
            revision="REV07",
            company="Neoenergia Pernambuco",
            pages=[p],
            full_clean_text="**[Página 1]**\n\nC",
            source_file="docs/info/DIS-NOR-030-REV07.md",
        )
        assert doc.document_code == "DIS-NOR-030"
        assert doc.revision == "REV07"
        assert doc.company == "Neoenergia Pernambuco"
        assert len(doc.pages) == 1


# ==============================================================================
# Testes de Formatação e Extração de Tabelas
# ==============================================================================


class TestTableUtilities:
    """Testes para conversão e extração de tabelas Markdown."""

    def test_format_table_as_markdown_valid(self) -> None:
        raw_table = [
            ["Tensão", "Demanda", "Disjuntor"],
            ["220/127 V", "10 kVA", "40 A"],
            ["380/220 V", "25 kVA", "63 A"],
        ]
        md = format_table_as_markdown(raw_table)
        assert "| Tensão | Demanda | Disjuntor |" in md
        assert "| --- | --- | --- |" in md
        assert "| 220/127 V | 10 kVA | 40 A |" in md

    def test_format_table_as_markdown_handles_none_and_ragged_rows(self) -> None:
        raw_table = [
            ["Col1", "Col2"],
            ["Val1", None],
            ["Val2", "Val3", "ExtraVal"],
        ]
        md = format_table_as_markdown(raw_table)
        assert "| Col1 | Col2 |" in md
        assert "| Val1 |  |" in md
        assert "| Val2 | Val3 | ExtraVal |" in md

    def test_format_table_as_markdown_empty(self) -> None:
        assert format_table_as_markdown([]) == ""

    def test_extract_markdown_tables(self) -> None:
        md_text = (
            "Parágrafo antes da tabela\n\n"
            "| Col1 | Col2 |\n"
            "| --- | --- |\n"
            "| A | B |\n\n"
            "Parágrafo intermediário\n\n"
            "| X | Y |\n"
            "| --- | --- |\n"
            "| 1 | 2 |"
        )
        tables = extract_markdown_tables(md_text)
        assert len(tables) == 2
        assert "| Col1 | Col2 |" in tables[0]
        assert "| X | Y |" in tables[1]


# ==============================================================================
# Testes do Parser de Markdown com Arquivos Reais
# ==============================================================================


class TestMarkdownParser:
    """Testes do parser de documentos Markdown utilizando arquivos normativos reais."""

    def test_parse_markdown_dis_nor_030(self) -> None:
        assert DIS_NOR_030_MD.is_file(), f"Arquivo não encontrado: {DIS_NOR_030_MD}"
        doc = parse_markdown_file(DIS_NOR_030_MD)

        assert doc.document_code == "DIS-NOR-030"
        assert "07" in doc.revision
        assert "Neoenergia" in doc.company
        assert len(doc.pages) > 50

        # Primeira página deve ter número 1
        assert doc.pages[0].page_number == 1
        # Não deve haver anomalias de cabeçalhos invertidos no texto consolidado
        assert "ro tn u js iD" not in doc.full_clean_text
        assert "o ã s n e T" not in doc.full_clean_text

        # Deve conter marcadores de página no texto consolidado
        assert "**[Página 1]**" in doc.full_clean_text
        assert "**[Página 2]**" in doc.full_clean_text

    def test_parse_markdown_dis_nor_053(self) -> None:
        assert DIS_NOR_053_MD.is_file(), f"Arquivo não encontrado: {DIS_NOR_053_MD}"
        doc = parse_markdown_file(DIS_NOR_053_MD)

        assert doc.document_code == "DIS-NOR-053"
        assert "06" in doc.revision
        assert len(doc.pages) > 50
        assert doc.pages[0].page_number == 1
        assert len(doc.full_clean_text) > 1000

    def test_parse_markdown_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            parse_markdown_file("caminho/inexistente/documento.md")


# ==============================================================================
# Testes do Parser de PDF (Sintético / Mock e Real)
# ==============================================================================


class TestPdfParser:
    """Testes do parser de documentos PDF com pdfplumber."""

    def test_parse_pdf_file_with_mock(self, tmp_path: Path) -> None:
        fake_pdf_path = tmp_path / "DIS-NOR-099-REV02.pdf"
        fake_pdf_path.write_bytes(b"%PDF-1.4 mock content")

        mock_page_1 = MagicMock()
        mock_page_1.extract_text.return_value = (
            "TÍTULO: Fornecimento em Média Tensão DIS-NOR-099 REV.: 02\n"
            "Norma técnica de distribuição Neoenergia Pernambuco."
        )
        mock_page_1.extract_tables.return_value = [[["Tensão", "Limite"], ["13,8 kV", "300 kVA"]]]

        mock_page_2 = MagicMock()
        mock_page_2.extract_text.return_value = "Página 2 com orientações e grandezas 3F 220V."
        mock_page_2.extract_tables.return_value = []

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page_1, mock_page_2]
        mock_pdf.__enter__.return_value = mock_pdf

        with patch("pdfplumber.open", return_value=mock_pdf):
            doc = parse_pdf_file(fake_pdf_path)

            assert doc.document_code == "DIS-NOR-099"
            assert doc.revision == "02" or doc.revision == "REV02"
            assert "Neoenergia" in doc.company
            assert len(doc.pages) == 2
            assert doc.pages[0].page_number == 1
            assert len(doc.pages[0].tables) == 1
            assert "| 13,8 kV | 300 kVA |" in doc.pages[0].tables[0]
            assert "**[Página 1]**" in doc.full_clean_text
            assert "**[Página 2]**" in doc.full_clean_text

    def test_parse_pdf_file_empty_pages_raises_error(self, tmp_path: Path) -> None:
        fake_pdf_path = tmp_path / "vazio.pdf"
        fake_pdf_path.write_bytes(b"%PDF-1.4")

        mock_pdf = MagicMock()
        mock_pdf.pages = []
        mock_pdf.__enter__.return_value = mock_pdf

        with patch("pdfplumber.open", return_value=mock_pdf):
            with pytest.raises(ValueError, match="vazio ou sem páginas"):
                parse_pdf_file(fake_pdf_path)

    def test_parse_pdf_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            parse_pdf_file("arquivo/inexistente.pdf")


# ==============================================================================
# Testes do Despachante Polimórfico (parse_document)
# ==============================================================================


class TestParseDocumentDispatcher:
    """Testes da função unificada parse_document."""

    def test_dispatch_to_markdown(self) -> None:
        doc = parse_document(DIS_NOR_030_MD)
        assert isinstance(doc, ParsedDocument)
        assert doc.document_code == "DIS-NOR-030"

    def test_dispatch_unsupported_format(self, tmp_path: Path) -> None:
        doc_file = tmp_path / "norma.docx"
        doc_file.write_text("conteúdo word")

        with pytest.raises(ValueError, match="Formato de arquivo não suportado"):
            parse_document(doc_file)

    def test_dispatch_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            parse_document("arquivo_que_nao_existe.md")
