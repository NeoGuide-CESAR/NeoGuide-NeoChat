"""Unit tests for normative document hybrid semantic chunking."""

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from lumi.ingestion.chunker import (
    chunk_document,
    chunk_table,
    parse_heading,
    recursive_split_text,
)
from lumi.ingestion.models import DocumentPage, NormativeChunkData, ParsedDocument
from lumi.ingestion.parser import parse_document

DOCS_INFO_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "info"
DIS_NOR_030_MD = DOCS_INFO_DIR / "DIS-NOR-030-REV07.md"
DIS_NOR_053_MD = DOCS_INFO_DIR / "DIS-NOR-053-REV06.md"


# ==============================================================================
# 1. Testes do Contrato Pydantic: NormativeChunkData
# ==============================================================================


class TestNormativeChunkData:
    """Suíte de testes para o modelo Pydantic NormativeChunkData."""

    def test_normative_chunk_data_valid(self) -> None:
        content = (
            "[Norma: DIS-NOR-030 | Rev: 07 | Seção: 5.2 - Distribuidoras Nordeste | Pág: 5]\n\n"
            "Texto normativo das Distribuidoras Nordeste."
        )
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        chunk = NormativeChunkData(
            document_code="DIS-NOR-030",
            revision="07",
            content=content,
            section_code="5.2",
            section_title="Distribuidoras Nordeste",
            page_number=5,
            metadata={"is_table": False},
            chunk_hash=expected_hash,
        )

        assert chunk.document_code == "DIS-NOR-030"
        assert chunk.revision == "07"
        assert chunk.content == content
        assert chunk.section_code == "5.2"
        assert chunk.section_title == "Distribuidoras Nordeste"
        assert chunk.page_number == 5
        assert chunk.metadata["is_table"] is False
        assert chunk.chunk_hash == expected_hash

    def test_normative_chunk_data_auto_computes_hash(self) -> None:
        content = "Texto de teste sem hash explícito."
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        chunk = NormativeChunkData(
            document_code="DIS-NOR-053",
            revision="06",
            content=content,
        )

        assert chunk.chunk_hash == expected_hash

    def test_normative_chunk_data_immutability(self) -> None:
        chunk = NormativeChunkData(
            document_code="DIS-NOR-030",
            revision="07",
            content="Texto imutável",
        )
        with pytest.raises((ValidationError, TypeError)):
            # Tentar alterar qualquer atributo deve falhar
            chunk.document_code = "DIS-NOR-999"  # type: ignore[misc]

    def test_normative_chunk_data_page_number_validation(self) -> None:
        with pytest.raises(ValidationError):
            NormativeChunkData(
                document_code="DIS-NOR-030",
                revision="07",
                content="Texto com página zero",
                page_number=0,
            )

        with pytest.raises(ValidationError):
            NormativeChunkData(
                document_code="DIS-NOR-030",
                revision="07",
                content="Texto com página negativa",
                page_number=-5,
            )

    def test_normative_chunk_data_defaults(self) -> None:
        chunk = NormativeChunkData(
            document_code="DIS-NOR-030",
            revision="07",
            content="Texto básico",
        )
        assert chunk.section_code is None
        assert chunk.section_title is None
        assert chunk.page_number is None
        assert chunk.metadata == {}
        assert len(chunk.chunk_hash) == 64


# ==============================================================================
# 2. Testes de Identificação e Parsing de Títulos Normativos
# ==============================================================================


class TestHeadingParsing:
    """Suíte de testes para detecção de títulos e itens normativos."""

    def test_parse_markdown_headings_with_numeric_codes(self) -> None:
        assert parse_heading("### 1. CONTROLE DE ALTERAÇÕES") == (1, "1", "CONTROLE DE ALTERAÇÕES")
        assert parse_heading("### 5. DEFINIÇÕES") == (1, "5", "DEFINIÇÕES")
        assert parse_heading("### 5.1 Distribuidora") == (2, "5.1", "Distribuidora")
        assert parse_heading("#### 5.2.1 Desconectáveis") == (3, "5.2.1", "Desconectáveis")
        assert parse_heading("##### 6.1.1.1 Esta norma se aplica") == (
            4,
            "6.1.1.1",
            "Esta norma se aplica",
        )

    def test_parse_plain_text_numbered_items(self) -> None:
        assert parse_heading("5.2 Distribuidoras Nordeste") == (2, "5.2", "Distribuidoras Nordeste")
        assert parse_heading("6.7.16 Instalações em Áreas Comuns") == (
            3,
            "6.7.16",
            "Instalações em Áreas Comuns",
        )

    def test_parse_capitulo_and_anexo(self) -> None:
        res_cap = parse_heading("### Capítulo X - Das Disposições Finais")
        assert res_cap is not None
        assert res_cap[1] == "Capítulo X"
        assert res_cap[2] == "Das Disposições Finais"

        res_anexo = parse_heading("## Anexo III. Tabelas de Carga")
        assert res_anexo is not None
        assert res_anexo[1] == "Anexo III"
        assert "Tabelas de Carga" in res_anexo[2]

    def test_parse_headings_without_code(self) -> None:
        assert parse_heading("### SUMÁRIO") == (3, None, "SUMÁRIO")
        assert parse_heading("# INTRODUÇÃO GERAL") == (1, None, "INTRODUÇÃO GERAL")

    def test_parse_non_headings_return_none(self) -> None:
        assert parse_heading("Apenas um texto explicativo qualquer.") is None
        assert parse_heading("| Coluna 1 | Coluna 2 |") is None
        assert parse_heading("") is None
        assert parse_heading("   ") is None


# ==============================================================================
# 3. Testes do Algoritmo de Divisão Recursiva Textual
# ==============================================================================


class TestRecursiveTextSplitter:
    """Suíte de testes para subdivisão recursiva com overlap."""

    def test_short_text_remains_single_piece(self) -> None:
        short_text = "Este é um texto curto que cabe integralmente no chunk."
        pieces = recursive_split_text(short_text, chunk_size=1000, chunk_overlap=150)
        assert len(pieces) == 1
        assert pieces[0] == short_text

    def test_long_text_splits_with_overlap(self) -> None:
        p1 = "Parágrafo primeiro contendo informações detalhadas sobre a rede elétrica. " * 10
        p2 = "Parágrafo segundo com especificações técnicas e parâmetros de condutores. " * 10
        full_text = f"{p1}\n\n{p2}"

        pieces = recursive_split_text(full_text, chunk_size=500, chunk_overlap=100)
        assert len(pieces) > 1
        for p in pieces:
            assert len(p) <= 600  # tolerância leve para corte em palavras/parágrafos

        # Verifica presença de overlap entre blocos contíguos
        tail = pieces[0][-50:]
        assert any(word in pieces[1] for word in tail.split() if len(word) > 5)

    def test_empty_or_whitespace_text(self) -> None:
        assert recursive_split_text("", chunk_size=1000, chunk_overlap=150) == []
        assert recursive_split_text("   \n\n  ", chunk_size=1000, chunk_overlap=150) == []


# ==============================================================================
# 4. Testes de Tratamento Especializado de Tabelas
# ==============================================================================


class TestTableChunking:
    """Suíte de testes para atomicidade e split lógico de tabelas Markdown."""

    def test_atomic_table_within_threshold(self) -> None:
        table = (
            "| Categoria | Tensão | Carga (kW) |\n"
            "| --- | --- | --- |\n"
            "| M1 | 220 V | 10 |\n"
            "| M2 | 380 V | 25 |"
        )
        sub_chunks = chunk_table(
            table_text=table,
            table_id="tabela_1",
            document_code="DIS-NOR-030",
            revision="07",
            section_code="6.4",
            section_title="Carga Instalada",
            page_number=17,
            max_table_chars=2000,
        )

        assert len(sub_chunks) == 1
        chunk = sub_chunks[0]
        assert chunk.metadata["is_table"] is True
        assert chunk.metadata["table_id"] == "tabela_1"
        assert "| Categoria | Tensão | Carga (kW) |" in chunk.content
        assert "| M2 | 380 V | 25 |" in chunk.content
        assert (
            "[Norma: DIS-NOR-030 | Rev: 07 | Seção: 6.4 - Carga Instalada | Pág: 17]"
            in chunk.content
        )

    def test_giant_table_splits_and_replicates_header(self) -> None:
        header = "| Código | Descrição do Equipamento | Potência (W) | Quantidade |\n| --- | --- | --- | --- |"
        rows = [
            f"| IT{i:03d} | Equipamento Normativo Modelo {i} | {100 * i} W | {i} |"
            for i in range(1, 40)
        ]
        giant_table = header + "\n" + "\n".join(rows)
        assert len(giant_table) > 2000

        sub_chunks = chunk_table(
            table_text=giant_table,
            table_id="tabela_equipamentos",
            document_code="DIS-NOR-030",
            revision="07",
            section_code="6.26",
            section_title="Cálculo da Carga",
            page_number=45,
            max_table_chars=1000,
        )

        assert len(sub_chunks) > 1
        for idx, sc in enumerate(sub_chunks, start=1):
            assert sc.metadata["is_table"] is True
            assert sc.metadata["table_id"] == "tabela_equipamentos"
            assert sc.metadata["table_part"] == idx
            assert sc.metadata["total_parts"] == len(sub_chunks)
            # REPLICAÇÃO OBRIGATÓRIA DO CABEÇALHO EM CADA SUB-CHUNK
            assert "| Código | Descrição do Equipamento | Potência (W) | Quantidade |" in sc.content
            assert "| --- | --- | --- | --- |" in sc.content
            assert (
                "[Norma: DIS-NOR-030 | Rev: 07 | Seção: 6.26 - Cálculo da Carga | Pág: 45]"
                in sc.content
            )


# ==============================================================================
# 5. Testes de Rastreamento de Marcadores de Página
# ==============================================================================


class TestPageTracking:
    """Suíte de testes para detecção contínua de páginas e ranges."""

    def test_chunking_tracks_single_page(self) -> None:
        doc = ParsedDocument(
            document_code="DIS-NOR-030",
            title="Norma de Teste",
            revision="07",
            company="Neoenergia",
            pages=[
                DocumentPage(
                    page_number=5,
                    raw_text="",
                    clean_text="### 5.1 Distribuidora\nTexto exclusivo da página 5.",
                )
            ],
            full_clean_text="**[Página 5]**\n\n### 5.1 Distribuidora\nTexto exclusivo da página 5.",
            source_file="test.md",
        )

        chunks = chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].page_number == 5
        assert "page_range" not in chunks[0].metadata
        assert (
            "[Norma: DIS-NOR-030 | Rev: 07 | Seção: 5.1 - Distribuidora | Pág: 5]"
            in chunks[0].content
        )
        # O marcador artificial não deve poluir o corpo textual
        assert "**[Página 5]**" not in chunks[0].content

    def test_chunking_tracks_multi_page_span(self) -> None:
        doc = ParsedDocument(
            document_code="DIS-NOR-030",
            title="Norma de Teste",
            revision="07",
            company="Neoenergia",
            pages=[],
            full_clean_text=(
                "**[Página 1]**\n\n"
                "### 5.1 Seção Longa\n"
                "Início do texto na primeira página antes da quebra.\n\n"
                "**[Página 2]**\n\n"
                "Continuação direta do texto na segunda página sem quebra de seção."
            ),
            source_file="test.md",
        )

        chunks = chunk_document(doc, chunk_size=2000)
        assert len(chunks) == 1
        assert chunks[0].page_number == 1
        assert chunks[0].metadata.get("page_range") == [1, 2]
        assert (
            "[Norma: DIS-NOR-030 | Rev: 07 | Seção: 5.1 - Seção Longa | Pág: 1]"
            in chunks[0].content
        )
        assert "**[Página 1]**" not in chunks[0].content
        assert "**[Página 2]**" not in chunks[0].content


# ==============================================================================
# 6. Testes End-to-End de chunk_document
# ==============================================================================


class TestChunkDocumentEndToEnd:
    """Suíte de testes integrados e validações de borda de chunk_document."""

    def test_chunk_document_validates_parameters(self) -> None:
        doc = ParsedDocument(
            document_code="DIS-NOR-030",
            title="Teste",
            revision="07",
            company="Neoenergia",
            pages=[],
            full_clean_text="Texto",
            source_file="test.md",
        )
        with pytest.raises(ValueError, match="chunk_size"):
            chunk_document(doc, chunk_size=0)

        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_document(doc, chunk_size=1000, chunk_overlap=-10)

        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_document(doc, chunk_size=1000, chunk_overlap=1000)

    def test_chunk_document_empty_content_returns_empty_list(self) -> None:
        doc = ParsedDocument(
            document_code="DIS-NOR-030",
            title="Teste",
            revision="07",
            company="Neoenergia",
            pages=[],
            full_clean_text="",
            source_file="test.md",
        )
        assert chunk_document(doc) == []

    def test_chunk_document_synthetic_normative_structure(self) -> None:
        synthetic_text = (
            "**[Página 5]**\n\n"
            "### 5. DEFINIÇÕES\n\n"
            "### 5.1 Distribuidora\n"
            "Empresa fornecedora dos serviços de distribuição.\n\n"
            "### 5.2 Distribuidoras Nordeste\n"
            "Neoenergia Coelba, Pernambuco e Cosern.\n\n"
            "| Cód | Nome |\n"
            "| --- | --- |\n"
            "| 01 | Neoenergia Pernambuco |\n\n"
            "Texto após a tabela no mesmo item."
        )

        doc = ParsedDocument(
            document_code="DIS-NOR-030",
            title="Norma Sintética",
            revision="07",
            company="Neoenergia",
            pages=[],
            full_clean_text=synthetic_text,
            source_file="test.md",
        )

        chunks = chunk_document(doc)
        assert len(chunks) >= 3

        # Valida que todos os chunks possuem hash SHA-256 válido
        for c in chunks:
            assert len(c.chunk_hash) == 64
            assert c.chunk_hash == hashlib.sha256(c.content.encode("utf-8")).hexdigest()

        # Valida identificação das seções
        sec_codes = [c.section_code for c in chunks]
        assert "5.1" in sec_codes
        assert "5.2" in sec_codes

        # Valida que a tabela foi isolada
        table_chunks = [c for c in chunks if c.metadata.get("is_table") is True]
        assert len(table_chunks) == 1
        assert "| 01 | Neoenergia Pernambuco |" in table_chunks[0].content
        assert table_chunks[0].section_code == "5.2"

    @pytest.mark.skipif(not DIS_NOR_030_MD.exists(), reason="Arquivo DIS-NOR-030 não encontrado")
    def test_chunk_document_real_dis_nor_030(self) -> None:
        doc = parse_document(DIS_NOR_030_MD)
        chunks = chunk_document(doc, chunk_size=1000, chunk_overlap=150)

        assert len(chunks) > 50
        # Todas as instâncias devem ter código e revisão
        for c in chunks:
            assert c.document_code == "DIS-NOR-030"
            assert c.revision in ("07", "REV07")
            assert c.content.startswith("[Norma: DIS-NOR-030")
            assert c.chunk_hash == hashlib.sha256(c.content.encode("utf-8")).hexdigest()

        # Deve conter tabelas normativas identificadas
        table_chunks = [c for c in chunks if c.metadata.get("is_table") is True]
        assert len(table_chunks) > 0

        # Deve conter seções normativas rastreadas
        known_sections = [c.section_code for c in chunks if c.section_code]
        assert any("5" in s for s in known_sections)
        assert any("6" in s for s in known_sections)

    @pytest.mark.skipif(not DIS_NOR_053_MD.exists(), reason="Arquivo DIS-NOR-053 não encontrado")
    def test_chunk_document_real_dis_nor_053(self) -> None:
        doc = parse_document(DIS_NOR_053_MD)
        chunks = chunk_document(doc, chunk_size=1000, chunk_overlap=150)

        assert len(chunks) > 100
        for c in chunks:
            assert c.document_code == "DIS-NOR-053"
            assert c.revision in ("06", "REV06")
            assert c.chunk_hash == hashlib.sha256(c.content.encode("utf-8")).hexdigest()
