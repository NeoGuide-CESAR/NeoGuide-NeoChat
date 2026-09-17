"""Guardrails de saída para auditoria determinística de citações e salvaguarda de cálculo.

Implementa validações assíncronas determinísticas pós-resposta para:
- Extração rápida de citações normativas (ex.: [Fonte: DIS-NOR-030, Item 5.3]);
- Detecção de conclusões numéricas absolutas de demanda sem direcionamento ao Wizard NeoGuide (RN-03);
- Cruzamento e auditoria com os fragmentos do banco vetorial (detecção de alucinações de normas/seções).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lumi.rag.retriever import RetrievedChunk

# ----------------------------------------------------------------------
# Estruturas de Dados
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class OutputGuardrailResult:
    """Resultado estruturado da validação de saída de guardrails."""

    is_valid: bool
    valid_citations: list[str] = field(default_factory=list)
    hallucinated_citations: list[str] = field(default_factory=list)
    has_calculation_violation: bool = False
    warning_flags: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
# Padrões Regex Pré-compilados
# ----------------------------------------------------------------------

# Citação no formato [Fonte: DIS-NOR-030, Item 5.3] ou (Fonte: DIS-NOR-030, Item 5.3)
RE_CITATION = re.compile(
    r"(?:\[|\()?\s*(?:Fonte|Fontes)\s*:\s*([A-Za-z0-9_-]+)(?:\s*,\s*([^\]\)\n]+?))?\s*(?:\]|\))",
    re.IGNORECASE,
)

# Menção ao Wizard ou NeoGuide para conformidade com a RN-03
RE_WIZARD_NEOGUIDE = re.compile(r"\b(?:wizard\s*neoguide|wizard|neoguide)\b", re.IGNORECASE)

# Padrões indicadores de conclusão numérica absoluta de demanda ou dimensionamento elétrico
RE_CALCULATION_PATTERNS = [
    re.compile(
        r"(?:demanda\s+(?:total|calculada|final|estimada|resultante|do\s+pr[eé]dio|da\s+edifica[cç][aã]o)?|dimensionamento\s+(?:final|total)?)"
        r"\s*(?:[eé]\s+de|[eé]|ser[aá]\s+de|ser[aá]|de|resulta\s+em|totaliza|ficou\s+em|[:=])\s*"
        r"(?:exatos?\s*)?(\d+(?:[.,]\d+)?)\s*(?:kva|kw|kvar|a|amperes?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bexatos?\s+(\d+(?:[.,]\d+)?)\s*(?:kva|kw|kvar|a|amperes?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:c[aá]lculo|calculou-se|calculado)\s+(?:da\s+demanda\s+)?(?:total\s+)?(?:resulta\s+em|de|d[aá]|totaliza)?\s*(\d+(?:[.,]\d+)?)\s*(?:kva|kw|kvar|a|amperes?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:resultado\s+(?:do\s+c[aá]lculo|final)?)\s*(?:[eé]|de|resulta\s+em|[:=])\s*(\d+(?:[.,]\d+)?)\s*(?:kva|kw|kvar|a|amperes?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:total\s+de|totalizando)\s+(\d+(?:[.,]\d+)?)\s*(?:kva|kw|kvar|a|amperes?)\s+(?:de\s+demanda|para\s+a\s+demanda)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:demanda|dimensionamento)\s*(?:total|final)?\s*[:=]\s*(\d+(?:[.,]\d+)?)\s*(?:kva|kw|a)\b",
        re.IGNORECASE,
    ),
]


# ----------------------------------------------------------------------
# Funções de Extração e Validação
# ----------------------------------------------------------------------


def extract_citations(text: str) -> list[tuple[str, str]]:
    """Extrai referências normativas do texto da resposta gerada.

    Captura padrões do tipo:
    - [Fonte: DIS-NOR-030, Item 5.3]
    - [Fonte: DIS-NOR-030, Item 5.2, Pág. 14]
    - (Fonte: DIS-NOR-030, 5.3)
    - [Fonte: DIS-NOR-030]

    Returns:
        list[tuple[str, str]]: Lista única ordenada de tuplas (document_code, section_code).
    """
    citations: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for match in RE_CITATION.finditer(text):
        doc_code = match.group(1).strip().upper()
        sec_raw = match.group(2).strip() if match.group(2) else ""

        # Remove sufixos de paginação (ex.: ', Pág. 28' ou ', Pag 28')
        sec_clean = re.sub(r",\s*p[aá]g(?:ina)?\.?\s*\d+", "", sec_raw, flags=re.IGNORECASE).strip()

        item = (doc_code, sec_clean)
        if item not in seen:
            seen.add(item)
            citations.append(item)

    return citations


def check_calculation_safeguard(text: str) -> bool:
    """Detecta cálculos numéricos absolutos de demanda/dimensionamento sem menção ao Wizard NeoGuide (RN-03).

    Returns:
        bool: True se for detectada violação (cálculo presente SEM menção ao Wizard NeoGuide);
              False se a resposta estiver em conformidade ou não contiver cálculos numéricos absolutos.
    """
    # 1. Se menciona o Wizard ou o NeoGuide, cumpre a RN-03 delegando a responsabilidade de cálculo
    if RE_WIZARD_NEOGUIDE.search(text):
        return False

    # 2. Se não menciona o Wizard, verifica se emitiu resultados numéricos absolutos de cálculo
    for pattern in RE_CALCULATION_PATTERNS:
        if pattern.search(text):
            return True

    return False


def _normalize_section(sec: str) -> str:
    """Normaliza identificador de seção para comparação resiliente."""
    if not sec:
        return ""
    # Remove acentuação e converte para minúsculas
    nfkd = unicodedata.normalize("NFKD", sec.strip())
    s = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
    # Remove prefixos comuns (item, seção, secao, tabela, capítulo, etc.)
    s = re.sub(
        r"^(?:item|secao|sec|capitulo|cap|tabela|tab|artigo|art)\.?\s*",
        "",
        s,
    ).strip()
    return s


def _extract_numeric_prefix(sec: str) -> str:
    """Extrai prefixo numérico hierárquico como '5.3' ou '5.2.1' se presente."""
    m = re.match(r"^(\d+(?:\.\d+)*)", sec)
    return m.group(1) if m else ""


def _section_matches(
    cite_sec: str,
    chunk_sec_code: str | None,
    chunk_sec_title: str | None,
) -> bool:
    """Verifica se a seção citada corresponde ao código ou título do fragmento normativo."""
    if not cite_sec:
        # Citação genérica da norma sem especificação de item
        return True

    norm_cite = _normalize_section(cite_sec)
    norm_chunk_code = _normalize_section(chunk_sec_code or "")
    norm_chunk_title = _normalize_section(chunk_sec_title or "")

    # 1. Correspondência exata normalizada
    if norm_chunk_code and norm_cite == norm_chunk_code:
        return True

    # 2. Correspondência por prefixo numérico (ex.: '5.3' vs '5.3 — Dimensionamento')
    num_cite = _extract_numeric_prefix(norm_cite)
    num_chunk = _extract_numeric_prefix(norm_chunk_code)
    if num_cite and num_chunk and num_cite == num_chunk:
        return True

    # 3. Correspondência textual em título da seção
    if norm_cite and norm_chunk_title and (norm_cite in norm_chunk_title):
        return True

    return False


def validate_output(
    response_text: str,
    retrieved_chunks: list[RetrievedChunk] | list[dict[str, Any]] | None = None,
) -> OutputGuardrailResult:
    """Valida deterministicamente as saídas da LLM cruzando com o contexto documental e salvaguardas.

    - Extrai e valida todas as citações [Fonte: DOC, SEC] contra os chunks disponíveis no contexto.
    - Detecta alucinações de códigos normativos ou itens inexistentes nos fragmentos recuperados.
    - Avalia a salvaguarda de responsabilidade de cálculo numérico (RN-03).

    Args:
        response_text: Texto completo gerado pelo assistente.
        retrieved_chunks: Lista de fragmentos recuperados (RetrievedChunk) ou metadados de fontes.

    Returns:
        OutputGuardrailResult estruturado e imutável.
    """
    citations = extract_citations(response_text)
    has_calc_violation = check_calculation_safeguard(response_text)

    # Coleta fragmentos normalizados para auditoria
    chunks_data: list[tuple[str, str | None, str | None]] = []
    for c in retrieved_chunks or []:
        if isinstance(c, dict):
            # Dicionário de metadados de fonte
            doc = str(c.get("document_code", "")).strip().upper()
            sec_code = c.get("section_code") or c.get("section")
            sec_title = c.get("section_title")
        else:
            # Objeto RetrievedChunk
            raw_doc = getattr(c, "document_code", "")
            doc = str(raw_doc).strip().upper() if raw_doc else ""
            sec_code = getattr(c, "section_code", None)
            sec_title = getattr(c, "section_title", None)
        chunks_data.append((doc, sec_code, sec_title))

    valid_citations: list[str] = []
    hallucinated_citations: list[str] = []

    for cite_doc, cite_sec in citations:
        formatted_cite = (
            f"[Fonte: {cite_doc}, {cite_sec}]" if cite_sec else f"[Fonte: {cite_doc}]"
        )

        # Filtra chunks pertencentes ao documento citado
        matching_chunks = [c for c in chunks_data if c[0] == cite_doc]

        if not matching_chunks:
            # Documento normativo não consta em nenhum fragmento recuperado
            hallucinated_citations.append(formatted_cite)
            continue

        # Verifica se alguma seção dos fragmentos do documento coincide com a citada
        is_matched = False
        for _, chunk_sec_code, chunk_sec_title in matching_chunks:
            if _section_matches(cite_sec, chunk_sec_code, chunk_sec_title):
                is_matched = True
                break

        if is_matched:
            valid_citations.append(formatted_cite)
        else:
            hallucinated_citations.append(formatted_cite)

    warning_flags: list[str] = []
    if hallucinated_citations:
        warning_flags.append("HALLUCINATED_CITATION")
    if has_calc_violation:
        warning_flags.append("CALCULATION_WITHOUT_WIZARD")

    is_valid = (len(hallucinated_citations) == 0) and (not has_calc_violation)

    return OutputGuardrailResult(
        is_valid=is_valid,
        valid_citations=valid_citations,
        hallucinated_citations=hallucinated_citations,
        has_calculation_violation=has_calc_violation,
        warning_flags=warning_flags,
    )
