"""Testes unitários para guardrails de saída, extração de citações e salvaguarda de cálculo."""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from lumi.rag.output_guardrails import (
    OutputGuardrailResult,
    check_calculation_safeguard,
    extract_citations,
    validate_output,
)
from lumi.rag.retriever import RetrievedChunk


@pytest.fixture
def sample_chunks() -> list[RetrievedChunk]:
    """Cria fragmentos normativos simulados para validação cruzada."""
    chunk1 = RetrievedChunk(
        chunk_id=uuid4(),
        document_code="DIS-NOR-030",
        document_title="Norma Técnica de Distribuição",
        revision="REV07",
        section_code="Item 5.2",
        section_title="Queda de Tensão Admissível",
        page_number=14,
        content="A queda de tensão máxima admissível é de 5%.",
        similarity_score=0.92,
        metadata={},
    )
    chunk2 = RetrievedChunk(
        chunk_id=uuid4(),
        document_code="DIS-NOR-030",
        document_title="Norma Técnica de Distribuição",
        revision="REV07",
        section_code="5.3",
        section_title="Dimensionamento de Edificações Coletivas",
        page_number=28,
        content="Para edificações com mais de 24 unidades, aplicar Tabela 4.",
        similarity_score=0.89,
        metadata={},
    )
    chunk3 = RetrievedChunk(
        chunk_id=uuid4(),
        document_code="DIS-NOR-053",
        document_title="Compartilhamento de Infraestrutura",
        revision="REV04",
        section_code="Item 6.1",
        section_title="Afastamento de Telecomunicações",
        page_number=10,
        content="O afastamento vertical mínimo para redes de telecomunicação é de 600 mm.",
        similarity_score=0.85,
        metadata={},
    )
    return [chunk1, chunk2, chunk3]


class TestExtractCitations:
    """Testes de extração determinística de citações normativas via regex."""

    def test_extract_single_citation_standard(self) -> None:
        """Deve extrair citação no formato padrão [Fonte: DOC, Item SEC]."""
        text = "O limite admissível é de 5% [Fonte: DIS-NOR-030, Item 5.2]."
        citations = extract_citations(text)
        assert len(citations) == 1
        assert citations[0] == ("DIS-NOR-030", "Item 5.2")

    def test_extract_citation_with_page(self) -> None:
        """Deve extrair citação contendo menção a página, higienizando a paginação."""
        text = "Conforme [Fonte: DIS-NOR-030, Item 5.3, Pág. 28], para edifícios coletivos..."
        citations = extract_citations(text)
        assert len(citations) == 1
        assert citations[0] == ("DIS-NOR-030", "Item 5.3")

    def test_extract_multiple_citations(self) -> None:
        """Deve extrair múltiplas citações de normas distintas no mesmo texto."""
        text = (
            "Veja os critérios da queda [Fonte: DIS-NOR-030, Item 5.2] e os "
            "afastamentos mínimos em postes [Fonte: DIS-NOR-053, Item 6.1]."
        )
        citations = extract_citations(text)
        assert len(citations) == 2
        assert ("DIS-NOR-030", "Item 5.2") in citations
        assert ("DIS-NOR-053", "Item 6.1") in citations

    def test_extract_citation_parentheses(self) -> None:
        """Deve extrair citação delimitada por parênteses (Fonte: DOC, Item SEC)."""
        text = "Critério normativo (Fonte: DIS-NOR-030, Item 4.2)."
        citations = extract_citations(text)
        assert len(citations) == 1
        assert citations[0] == ("DIS-NOR-030", "Item 4.2")

    def test_extract_citation_numeric_section_only(self) -> None:
        """Deve extrair citação com seção puramente numérica [Fonte: DIS-NOR-030, 5.3]."""
        text = "Conforme [Fonte: DIS-NOR-030, 5.3]."
        citations = extract_citations(text)
        assert len(citations) == 1
        assert citations[0] == ("DIS-NOR-030", "5.3")

    def test_extract_citation_table_or_section(self) -> None:
        """Deve extrair citação com referência a tabelas [Fonte: DIS-NOR-030, Tabela 4]."""
        text = "Aplicar os fatores da [Fonte: DIS-NOR-030, Tabela 4]."
        citations = extract_citations(text)
        assert len(citations) == 1
        assert citations[0] == ("DIS-NOR-030", "Tabela 4")

    def test_extract_citation_without_section(self) -> None:
        """Deve extrair citação que mencione apenas a norma geral [Fonte: DIS-NOR-030]."""
        text = "De acordo com a norma geral [Fonte: DIS-NOR-030]."
        citations = extract_citations(text)
        assert len(citations) == 1
        assert citations[0] == ("DIS-NOR-030", "")

    def test_extract_no_citations_conversational(self) -> None:
        """Deve retornar lista vazia para texto conversacional sem citações formais."""
        text = "Olá! Como posso ajudar você com as normas da Neoenergia hoje?"
        citations = extract_citations(text)
        assert citations == []


class TestCheckCalculationSafeguard:
    """Testes de detecção de conclusões numéricas absolutas de cálculo (RN-03)."""

    def test_detects_absolute_demand_calculation_violation(self) -> None:
        """Deve detectar violação quando a LLM fornece valor absoluto de demanda sem Wizard."""
        text = "A demanda do seu prédio é de exatos 142,5 kVA."
        assert check_calculation_safeguard(text) is True

    def test_detects_total_calculated_demand_without_wizard(self) -> None:
        """Deve detectar violação quando indica demanda calculada em kW/kVA."""
        text = "O cálculo da demanda total resulta em 85 kVA."
        assert check_calculation_safeguard(text) is True

    def test_detects_dimensioning_amperes_violation(self) -> None:
        """Deve detectar violação quando fornece dimensionamento final em amperes."""
        text = "Portanto, o dimensionamento final é de 150 A para a entrada."
        assert check_calculation_safeguard(text) is True

    def test_passes_when_referencing_wizard_neoguide(self) -> None:
        """Não deve acusar violação se houver direcionamento ao Wizard NeoGuide."""
        text = (
            "A demanda preliminar estimada é de 142,5 kVA. No entanto, para obter a homologação "
            "e o memorial definitivo de cálculo, utilize o Wizard NeoGuide."
        )
        assert check_calculation_safeguard(text) is False

    def test_passes_when_referencing_neoguide(self) -> None:
        """Não deve acusar violação se houver menção ao NeoGuide."""
        text = "O resultado preliminar totaliza 80 kW. Recomendamos preencher os dados no NeoGuide."
        assert check_calculation_safeguard(text) is False

    def test_passes_methodological_explanation_without_calculation(self) -> None:
        """Não deve acusar violação em explicações normativas sem resultados numéricos finais."""
        text = (
            "Para dimensionar um edifício com 40 apartamentos, consulte a Tabela 4 da DIS-NOR-030, "
            "identifique a faixa de consumo e aplique o fator de diversidade correspondente."
        )
        assert check_calculation_safeguard(text) is False


class TestValidateOutput:
    """Testes da função central validate_output cruzando citações com fragmentos."""

    def test_validate_output_clean_and_valid(self, sample_chunks: list[RetrievedChunk]) -> None:
        """Resposta com citações legítimas presentes nos chunks deve ser válida."""
        text = (
            "O limite admissível de queda de tensão é de 5% [Fonte: DIS-NOR-030, Item 5.2]. "
            "Para o vão de telecomunicação, mantenha 600 mm [Fonte: DIS-NOR-053, Item 6.1]."
        )
        result = validate_output(text, retrieved_chunks=sample_chunks)

        assert isinstance(result, OutputGuardrailResult)
        assert result.is_valid is True
        assert len(result.valid_citations) == 2
        assert len(result.hallucinated_citations) == 0
        assert result.has_calculation_violation is False
        assert result.warning_flags == []

    def test_validate_output_normalizes_section_variants(
        self, sample_chunks: list[RetrievedChunk]
    ) -> None:
        """Deve validar com sucesso variações normativas (ex.: '5.3' vs 'Item 5.3')."""
        text = "Consulte os critérios de uso coletivo [Fonte: DIS-NOR-030, Item 5.3]."
        # sample_chunks possui chunk2 com section_code="5.3"
        result = validate_output(text, retrieved_chunks=sample_chunks)

        assert result.is_valid is True
        assert len(result.valid_citations) == 1
        assert len(result.hallucinated_citations) == 0

    def test_validate_output_detects_hallucinated_section(
        self, sample_chunks: list[RetrievedChunk]
    ) -> None:
        """Citação com seção inexistente nos fragmentos deve ser sinalizada como alucinação."""
        text = "Conforme o regulamento [Fonte: DIS-NOR-030, Item 99.4], instale os barramentos."
        result = validate_output(text, retrieved_chunks=sample_chunks)

        assert result.is_valid is False
        assert len(result.hallucinated_citations) == 1
        assert "DIS-NOR-030" in result.hallucinated_citations[0]
        assert "99.4" in result.hallucinated_citations[0]
        assert "HALLUCINATED_CITATION" in result.warning_flags

    def test_validate_output_detects_hallucinated_document(
        self, sample_chunks: list[RetrievedChunk]
    ) -> None:
        """Citação com norma não recuperada no contexto deve ser sinalizada como alucinação."""
        text = "Conforme norma externa [Fonte: DIS-NOR-999, Item 1.0]."
        result = validate_output(text, retrieved_chunks=sample_chunks)

        assert result.is_valid is False
        assert len(result.hallucinated_citations) == 1
        assert "DIS-NOR-999" in result.hallucinated_citations[0]
        assert "HALLUCINATED_CITATION" in result.warning_flags

    def test_validate_output_detects_calculation_violation(
        self, sample_chunks: list[RetrievedChunk]
    ) -> None:
        """Deve sinalizar violação de cálculo numérico desacompanhado de menção ao Wizard."""
        text = (
            "A queda máxima é de 5% [Fonte: DIS-NOR-030, Item 5.2]. "
            "A demanda total do seu prédio é de exatos 142,5 kVA."
        )
        result = validate_output(text, retrieved_chunks=sample_chunks)

        assert result.is_valid is False
        assert result.has_calculation_violation is True
        assert "CALCULATION_WITHOUT_WIZARD" in result.warning_flags
        # A citação 5.2 é válida, mas o resultado global é inválido devido ao cálculo
        assert len(result.valid_citations) == 1

    def test_validate_output_accepts_dict_sources(self) -> None:
        """validate_output deve suportar fontes passadas como lista de dicionários."""
        dict_sources = [
            {"document_code": "DIS-NOR-030", "section": "Item 5.2", "page": 14},
        ]
        text = "O valor máximo é 5% [Fonte: DIS-NOR-030, Item 5.2]."
        result = validate_output(text, retrieved_chunks=dict_sources)

        assert result.is_valid is True
        assert len(result.valid_citations) == 1

    def test_validate_output_with_empty_or_none_chunks(self) -> None:
        """Citação sem qualquer chunk recuperado deve ser classificada como alucinação."""
        text = "Conforme [Fonte: DIS-NOR-030, Item 5.2]."
        result = validate_output(text, retrieved_chunks=[])

        assert result.is_valid is False
        assert len(result.hallucinated_citations) == 1
        assert "HALLUCINATED_CITATION" in result.warning_flags

    def test_validate_output_conversational_text_without_citations(self) -> None:
        """Texto puramente conversacional sem citações é válido se não contiver violação de cálculo."""
        text = "Olá! Como posso ajudar você hoje?"
        result = validate_output(text, retrieved_chunks=[])

        assert result.is_valid is True
        assert result.valid_citations == []
        assert result.hallucinated_citations == []
        assert result.has_calculation_violation is False
        assert result.warning_flags == []

    def test_output_guardrail_result_is_frozen(self) -> None:
        """OutputGuardrailResult deve ser imutável (frozen dataclass)."""
        result = OutputGuardrailResult(
            is_valid=True,
            valid_citations=["[Fonte: DIS-NOR-030, Item 5.2]"],
            hallucinated_citations=[],
            has_calculation_violation=False,
            warning_flags=[],
        )
        with pytest.raises(FrozenInstanceError):
            result.is_valid = False  # type: ignore[misc]
