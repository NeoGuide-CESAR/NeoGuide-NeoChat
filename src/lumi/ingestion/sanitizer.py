"""Pure functions for cleaning, sanitizing, and normalizing technical normative text."""

import re
import unicodedata
from collections.abc import Sequence

from lumi.ingestion.models import DocumentPage

# Mapeamento ordenado de padrões de OCR com caracteres ou palavras invertidas
# Encontrados frequentemente em tabelas verticais ou digitalizações das normas Neoenergia.
REVERSED_OCR_PATTERNS: tuple[tuple[str, str], ...] = (
    # Expressões completas de cabeçalho
    (
        r"o\s+t\s+n\s+e\s+m\s+ic\s+e\s+n\s+ro\s+F\s+e\s+d\s+o\s+[ã\uFFFD\?]\s+s\s+n\s+e\s+T",
        "Tensão de Fornecimento",
    ),
    (r"\)\s*W\s*k\s*\(\s*a\s+d\s+a\s+la\s+t?\s*s\s+n\s+I\s+a\s+g\s+ra\s+C", "Carga Instalada (kW)"),
    (r"a\s+g\s+ra\s+C\s+a\s+d\s+a\s+la\s+t?\s*s\s+n\s+I\s*\(\s*k\s*W\s*\)", "Carga Instalada (kW)"),
    (r"\(\s*k\s*W\s*\)\s+Instalada\s+Carga", "Carga Instalada (kW)"),
    (r"\)A\s*\(\s*ro\s+t?\s*n\s+u\s+js\s+iD", "Disjuntor (A)"),
    (r"ro\s+t?\s*n\s+u\s+js\s+iD\s*\(\s*A\s*\)", "Disjuntor (A)"),
    (r"\)\s*A\s*\(\s*ro\s+t?\s*n\s+u\s+js\s+iD", "Disjuntor (A)"),
    (r"ro\s+t?\s*n\s+u\s+js\s+iD", "Disjuntor"),
    # Categoria e Carga
    (r"a\s+iro\s+g\s+e\s+t?\s*a\s+C", "Categoria"),
    (r"a\s+d\s+a\s+la\s+t?\s*s\s+n\s+I", "Instalada"),
    (r"a\s+g\s+ra\s+C", "Carga"),
    (r"a\s+d\s+n\s+a\s+m\s+e\s+D", "Demanda"),
    # Unidades e Grandezas
    (r"\)\s*W\s+k\s*\(", "(kW)"),
    (r"\)\s*A\s+V\s+k\s*\(", "(kVA)"),
    (r"V\s+7\s+2\s+1\s*/\s*0\s+2\s+2", "220 / 127 V"),
    (r"V\s+0\s+2\s+2\s*/\s*0\s+8\s+3", "380 / 220 V"),
    # Tensão e Finalidade
    (r"o\s+[ã\uFFFD\?]\s+s\s+n\s+e\s+[Tt]", "Tensão"),
    (r"o\s+d\s+a\s+d\s+il\s+a\s+n\s+i\s*F", "Finalidade"),
    (r"o\s+[ã\uFFFD\?]\s+[ç\uFFFD\?]\s+i?\s*d\s+e\s+M", "Medição"),
    # Condutores e Eletrodutos
    (r"s\s+o\s+t?\s*u\s+d\s+o\s+rte\s+lE", "Eletrodutos"),
    (r"o\s+tu\s+d\s+o\s+rte\s+lE", "Eletroduto"),
    (r"s\s+o\s+m\s+in\s+[í\uFFFD\?]\s*m?\s*M", "Mínimos"),
    (r"o\s+m\s+in\s+[í\uFFFD\?]\s*m?\s*M", "Mínimo"),
    (r"e\s+s\s+e\s+s\s+a\s+F", "Fases"),
    (r"s\s+e\s+s\s+a\s+F", "Fases"),
    (r"o\s+rtu\s+e\s+N", "Neutro"),
    (r"o?\s*tn\s+e\s+m\s+a\s+rre\s+tA", "Aterramento"),
    # Artefatos comuns de espaçamento
    (r"F\s+O\s*RNECIMENTO", "FORNECIMENTO"),
)

# Compilação dos padrões regex
COMPILED_REVERSED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in REVERSED_OCR_PATTERNS
]


def strip_toc_dots(text: str) -> str:
    """Remove pontilhados excessivos típicos de sumários e tabelas de conteúdo.

    Exemplo:
        '##### 1. CONTROLE DE ALTERAÇÕES ......... 3' -> '##### 1. CONTROLE DE ALTERAÇÕES 3'
        '..... 5' -> '5'
    """
    if not text:
        return ""

    # Substitui sequências de 3 ou mais pontos (com espaços opcionais entre eles)
    # preservando um espaço entre o texto precedente e posterior se houver
    dot_pattern = re.compile(r"[ \t]*(?:\.[ \t]*){3,}\.?")

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        # Se a linha for unicamente composta de pontos e espaços, ignora ou limpa
        stripped_line = line.strip()
        if re.fullmatch(r"(?:\.[ \t]*)+", stripped_line):
            continue

        cleaned = dot_pattern.sub(" ", line)
        # Limpa espaços horizontais duplicados gerados pela remoção
        cleaned = re.sub(r"[ \t]+", " ", cleaned).rstrip()
        cleaned_lines.append(cleaned)

    return "\n".join(cleaned_lines)


def fix_reversed_table_headers(text: str) -> str:
    """Corrige tokens e palavras invertidas por OCR em cabeçalhos de tabela.

    Exemplos:
        'o ã s n e T' -> 'Tensão'
        'a iro g e ta C' -> 'Categoria'
        ')A ( ro tn u js iD' -> 'Disjuntor (A)'
        'o d a d il a n iF' -> 'Finalidade'
    """
    if not text:
        return ""

    result = text
    for pattern, replacement in COMPILED_REVERSED_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


def normalize_unicode_and_spaces(text: str) -> str:
    """Normaliza caracteres Unicode e consolida espaços em branco repetitivos.

    Preserva explicitamente termos e grandezas de engenharia elétrica:
    3F, FN, FF, m², kVA, kW, kV, cv e pontuações decimais (ex.: 5,1 - 10).
    """
    if not text:
        return ""

    # Normalização Unicode NFC (preserva explicitamente o sobrescrito ² em m², acentuações, etc.)
    normalized = unicodedata.normalize("NFC", text)

    # Normaliza espaços em branco horizontais preservando quebras de linha
    lines: list[str] = []
    for line in normalized.splitlines():
        # Substitui múltiplos espaços e tabs horizontais por espaço único
        cleaned_line = re.sub(r"[^\S\r\n]+", " ", line).strip()
        lines.append(cleaned_line)

    # Junta as linhas e colapsa mais de 2 quebras de linha consecutivas
    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def inject_page_markers(pages: Sequence[DocumentPage]) -> str:
    """Concatena o conteúdo das páginas formatando delimitadores explícitos **[Página X]**.

    Exemplo:
        **[Página 1]**

        Texto da página 1...

        **[Página 2]**

        Texto da página 2...
    """
    sections: list[str] = []
    for page in pages:
        marker = f"**[Página {page.page_number}]**"
        content = page.clean_text.strip()
        if content:
            sections.append(f"{marker}\n\n{content}")
        else:
            sections.append(marker)

    return "\n\n".join(sections)
