"""Guardrails de entrada para proteção do assistente Lumi (NeoGuide).

Implementa validações determinísticas de baixa latência (< 5ms) para:
- Detecção e bloqueio de tentativas de Prompt Injection e Jailbreak;
- Sanitização de dados pessoais brasileiros (PII: CPF, CNPJ, Conta Contrato);
- Verificação de escopo temático (engenharia elétrica e normas Neoenergia).
"""

import re
import unicodedata
from dataclasses import dataclass, field

# ----------------------------------------------------------------------
# Estruturas de Dados
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class GuardrailResult:
    """Resultado estruturado da validação de entrada de guardrails."""

    is_allowed: bool
    sanitized_text: str
    rejection_reason: str | None = None
    detected_pii: list[str] = field(default_factory=list)
    is_injection: bool = False


# ----------------------------------------------------------------------
# Mensagens Padrão
# ----------------------------------------------------------------------

INJECTION_REJECTION_REASON = (
    "Tentativa de manipulação de instruções de segurança (prompt injection / jailbreak) "
    "detectada. Por políticas de segurança, sua solicitação foi recusada."
)

SCOPE_REJECTION_REASON = (
    "Sou a Lumi, assistente técnica especializada nas normas da Neoenergia Pernambuco "
    "(como DIS-NOR-030 e DIS-NOR-053) e engenharia de infraestrutura elétrica e telecomunicações. "
    "Não posso responder sobre temas fora do escopo normativo, como culinária, esportes ou astrologia. "
    "Por favor, envie sua dúvida sobre projetos elétricos ou normas técnicas."
)


# ----------------------------------------------------------------------
# Utilitários Internos
# ----------------------------------------------------------------------


def _normalize_text(text: str) -> str:
    """Normaliza o texto removendo diacríticos/acentos e convertendo para minúsculas."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


# ----------------------------------------------------------------------
# 1. Padrões de Sanitização de PII
# ----------------------------------------------------------------------

# CNPJ Formatado: XX.XXX.XXX/XXXX-XX
RE_CNPJ_FORMATTED = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")

# CPF Formatado: XXX.XXX.XXX-XX
RE_CPF_FORMATTED = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")

# Conta Contrato / Faturamento precedido por palavra-chave identificadora
# Ex: conta contrato: 7012345678, fatura nº 987654321, documento de faturamento 123456789
RE_CONTA_CONTRATO_LABELED = re.compile(
    r"(?i)\b(conta[\s_-]*contrato|n[ºo°]?\s*(?:da\s*)?conta|documento\s*(?:de\s*)?faturamento|fatura\s*(?:n[ºo°])?)"
    r"(\s*(?:[:#=-]|\b[eé]\b)?\s*)(\d{6,14})\b"
)

# CNPJ Desformatado: 14 dígitos numéricos contínuos isolados
RE_CNPJ_UNFORMATTED = re.compile(r"\b\d{14}\b")

# CPF Desformatado: 11 dígitos numéricos contínuos isolados
RE_CPF_UNFORMATTED = re.compile(r"\b\d{11}\b")


def sanitize_pii(text: str) -> tuple[str, list[str]]:
    """Detecta e substitui dados sensíveis por marcadores anônimos seguros.

    Ordem de substituição:
    1. CNPJ Formatado -> [CNPJ_REMOVIDO]
    2. CPF Formatado -> [CPF_REMOVIDO]
    3. Conta Contrato / Faturamento rotulado -> [CONTA_CONTRATO_REMOVIDA]
    4. CNPJ Desformatado (14 dígitos) -> [CNPJ_REMOVIDO]
    5. CPF Desformatado (11 dígitos) -> [CPF_REMOVIDO]

    Retorna:
        tuple[str, list[str]]: Texto sanitizado e lista única de categorias detectadas.
    """
    sanitized = text
    detected: list[str] = []

    # 1. CNPJ formatado
    if RE_CNPJ_FORMATTED.search(sanitized):
        sanitized = RE_CNPJ_FORMATTED.sub("[CNPJ_REMOVIDO]", sanitized)
        if "CNPJ" not in detected:
            detected.append("CNPJ")

    # 2. CPF formatado
    if RE_CPF_FORMATTED.search(sanitized):
        sanitized = RE_CPF_FORMATTED.sub("[CPF_REMOVIDO]", sanitized)
        if "CPF" not in detected:
            detected.append("CPF")

    # 3. Conta Contrato / Faturamento
    if RE_CONTA_CONTRATO_LABELED.search(sanitized):
        # Substitui mantendo o prefixo e o conector, mascarando apenas os dígitos
        sanitized = RE_CONTA_CONTRATO_LABELED.sub(r"\1\2[CONTA_CONTRATO_REMOVIDA]", sanitized)
        if "CONTA_CONTRATO" not in detected:
            detected.append("CONTA_CONTRATO")

    # 4. CNPJ desformatado (14 dígitos)
    if RE_CNPJ_UNFORMATTED.search(sanitized):
        sanitized = RE_CNPJ_UNFORMATTED.sub("[CNPJ_REMOVIDO]", sanitized)
        if "CNPJ" not in detected:
            detected.append("CNPJ")

    # 5. CPF desformatado (11 dígitos)
    if RE_CPF_UNFORMATTED.search(sanitized):
        sanitized = RE_CPF_UNFORMATTED.sub("[CPF_REMOVIDO]", sanitized)
        if "CPF" not in detected:
            detected.append("CPF")

    return sanitized, detected


# ----------------------------------------------------------------------
# 2. Padrões de Prompt Injection & Jailbreak
# ----------------------------------------------------------------------

# Padrões compilados para texto normalizado (sem acentos, minúsculas)
INJECTION_PATTERNS = [
    # Comandos de esquecimento de instruções em inglês
    re.compile(r"\bignore\s+(?:all\s+|the\s+|previous\s+)+instructions\b"),
    re.compile(r"\bdisregard\s+(?:all\s+|the\s+|previous\s+)+instructions\b"),
    re.compile(r"\bforget\s+(?:all\s+|the\s+|previous\s+)+instructions\b"),
    # Comandos de esquecimento de instruções em português
    re.compile(r"\bignore\s+(?:todas\s+as\s+|as\s+)?instrucoes\b"),
    re.compile(r"\bdesconsidere\s+(?:todas\s+as\s+|as\s+)?(?:instrucoes|regras|diretrizes)\b"),
    re.compile(r"\besqueca\s+(?:todas\s+as\s+|as\s+)?(?:instrucoes|regras|diretrizes)\b"),
    # Mudança forçada de persona para modo sem restrições
    re.compile(r"\bvoce\s+agora\s+e\s+(?:um\s+assistente\s+)?sem\s+regras\b"),
    re.compile(r"\bvoce\s+agora\s+e\s+(?:livre|irrestrito)\b"),
    re.compile(r"\bact\s+as\s+an?\s+unrestricted\b"),
    re.compile(r"\baja\s+como\s+(?:um\s+assistente\s+)?(?:sem\s+regras|livre|irrestrito)\b"),
    re.compile(r"\byou\s+are\s+now\s+(?:free|unrestricted)\b"),
    # DAN Mode e Jailbreak explícito
    re.compile(r"\b(?:you\s+are\s+now\s+in\s+|enable\s+)?dan\s+mode\b"),
    re.compile(r"\bdo\s+anything\s+now\b"),
    re.compile(r"\bjailbreak(?:\s+prompt)?\b"),
    # System Override e Modos de Desenvolvedor
    re.compile(r"\bsystem\s+override\b"),
    re.compile(r"\b(?:developer\s+mode\s+(?:on|enabled)|modo\s+desenvolvedor\s+ativado)\b"),
    re.compile(r"\bbypass\s+guardrails?\b"),
    # Exfiltração de System Prompt
    re.compile(r"\breveal\s+(?:your|the)\s+system\s+prompt\b"),
    re.compile(r"\bmostre\s+(?:seu|o)\s+system\s+prompt\b"),
    re.compile(r"\bquais\s+sao\s+suas\s+instrucoes\s+(?:de\s+|do\s+)?sistema\b"),
    re.compile(r"\bqual\s+e\s+o\s+seu\s+system\s+prompt\b"),
]


def detect_prompt_injection(text: str) -> tuple[bool, str | None]:
    """Analisa o texto contra padrões determinísticos de prompt injection e jailbreak.

    Retorna:
        tuple[bool, str | None]: (True, motivo) se for detectada injeção; (False, None) caso contrário.
    """
    normalized = _normalize_text(text)

    for pattern in INJECTION_PATTERNS:
        if pattern.search(normalized):
            return True, INJECTION_REJECTION_REASON

    return False, None


# ----------------------------------------------------------------------
# 3. Padrões de Verificação de Escopo Temático
# ----------------------------------------------------------------------

# Tópicos flagrantemente fora de escopo (normalizados)
OUT_OF_SCOPE_PATTERNS = [
    # Culinária e receitas
    re.compile(
        r"\b(?:receita\s+de\s+bolo|bolo\s+de\s+(?:cenoura|chocolate|fuba|laranja|milho|limao)|"
        r"como\s+fazer\s+(?:um\s+)?bolo|como\s+cozinhar|ingredientes\s+para\s+bolo|"
        r"cobertura\s+de\s+chocolate|receita\s+culinaria)\b"
    ),
    # Esportes e futebol
    re.compile(
        r"\b(?:campeonato\s+brasileiro|brasileirao|copa\s+do\s+mundo|jogo\s+de\s+futebol|"
        r"escalacao\s+do\s+(?:flamengo|palmeiras|corinthians|vasco|sport|nautico|santa\s+cruz|gremio|internacional)|"
        r"quem\s+ganhou\s+(?:o\s+)?(?:jogo|campeonato))\b"
    ),
    # Astrologia e horóscopo
    re.compile(
        r"\b(?:horoscopo|astrologia|mapa\s+astral|previsao\s+do\s+signo|astros\s+e\s+a\s+astrologia|"
        r"signo\s+de\s+(?:aries|touro|gemeos|cancer|leao|virgem|libra|escorpiao|sagitario|capricornio|aquario|peixes))\b"
    ),
    # Fofoca e entretenimento
    re.compile(
        r"\b(?:fofoca(?:\s+de|\s+dos)?\s+famosos|celebridades|big\s+brother\s+brasil|paredao\s+bbb)\b"
    ),
]

# Palavras-chave do domínio técnico de engenharia elétrica e telecomunicações
TECHNICAL_CONTEXT_KEYWORDS = [
    "dis-nor",
    "neoenergia",
    "disjuntor",
    "potencia",
    "kva",
    "mva",
    "kw",
    "tensao",
    "volt",
    "corrente",
    "ampere",
    "transformador",
    "trafo",
    "subestacao",
    "cabo",
    "condutor",
    "bitola",
    "eletroduto",
    "poste",
    "vao",
    "cruzeta",
    "telecom",
    "fibra",
    "aterramento",
    "spda",
    "demanda",
    "simultaneidade",
    "carga",
    "norma",
    "normativa",
    "nbr",
    "aneel",
    "medidor",
    "iluminacao",
    "memorial",
    "ramal",
    "instalacao",
]


def check_domain_scope(text: str) -> tuple[bool, str | None]:
    """Avalia se a consulta pertence ao escopo de engenharia/normas ou se deve ser recusada.

    Se a mensagem tocar em termos fora de escopo, mas contiver termos normativos ou elétricos
    (ex: iluminação de campo de futebol conforme normas), ela é permitida.

    Retorna:
        tuple[bool, str | None]: (True, None) se estiver no escopo; (False, motivo) se fora de escopo.
    """
    normalized = _normalize_text(text)

    # Verifica se aciona algum gatilho explícito de fora de escopo
    matches_out_of_scope = any(pat.search(normalized) for pat in OUT_OF_SCOPE_PATTERNS)

    if matches_out_of_scope:
        # Se contiver termos técnicos contextuais, permite
        has_technical_context = any(keyword in normalized for keyword in TECHNICAL_CONTEXT_KEYWORDS)
        if has_technical_context:
            return True, None

        return False, SCOPE_REJECTION_REASON

    return True, None


# ----------------------------------------------------------------------
# 4. Orquestrador Unificado
# ----------------------------------------------------------------------


def validate_input(text: str) -> GuardrailResult:
    """Orquestrador unificado de guardrails de entrada para a Lumi.

    Etapas executadas:
    1. Sanitização de PII brasileiro (substituição por placeholders e identificação de tipos);
    2. Detecção determinística de Prompt Injection e Jailbreak;
    3. Verificação de escopo temático com recusa educada para temas fora de contexto.

    Args:
        text: Pergunta ou mensagem bruta enviada pelo usuário.

    Returns:
        GuardrailResult: Estrutura contendo o status de permissão, texto sanitizado,
                         motivo de recusa (se houver), lista de PIIs e flag de injeção.
    """
    # 1. Sanitização de PII (executada prioritariamente para garantir que dados sensíveis
    # nunca transitem sem máscara, mesmo em tentativas de ataque)
    sanitized_text, detected_pii = sanitize_pii(text)

    # 2. Verificação de Prompt Injection / Jailbreak
    is_injection, injection_reason = detect_prompt_injection(text)
    if is_injection:
        return GuardrailResult(
            is_allowed=False,
            sanitized_text=sanitized_text,
            rejection_reason=injection_reason,
            detected_pii=detected_pii,
            is_injection=True,
        )

    # 3. Verificação de Escopo Temático
    is_in_scope, scope_reason = check_domain_scope(text)
    if not is_in_scope:
        return GuardrailResult(
            is_allowed=False,
            sanitized_text=sanitized_text,
            rejection_reason=scope_reason,
            detected_pii=detected_pii,
            is_injection=False,
        )

    # 4. Consulta aprovada para prosseguir para a busca semântica RAG
    return GuardrailResult(
        is_allowed=True,
        sanitized_text=sanitized_text,
        rejection_reason=None,
        detected_pii=detected_pii,
        is_injection=False,
    )
