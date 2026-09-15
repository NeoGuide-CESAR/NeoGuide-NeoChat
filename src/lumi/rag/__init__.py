"""Módulo RAG (Retrieval-Augmented Generation) e IA Segura da Lumi."""

from lumi.rag.guardrails import (
    GuardrailResult,
    check_domain_scope,
    detect_prompt_injection,
    sanitize_pii,
    validate_input,
)
from lumi.rag.llm_factory import (
    SUPPORTED_EMBEDDING_PROVIDERS,
    SUPPORTED_LLM_PROVIDERS,
    get_embeddings,
    get_llm,
    validate_embedding_dimension,
)
from lumi.rag.prompts import (
    CONTINGENCY_NO_SOURCES_MESSAGE,
    CONTINGENCY_NO_SOURCES_PROMPT,
    LUMI_SYSTEM_PROMPT,
    get_chat_prompt_template,
    get_rag_prompt_template,
)

__all__ = [
    "CONTINGENCY_NO_SOURCES_MESSAGE",
    "CONTINGENCY_NO_SOURCES_PROMPT",
    "GuardrailResult",
    "LUMI_SYSTEM_PROMPT",
    "SUPPORTED_EMBEDDING_PROVIDERS",
    "SUPPORTED_LLM_PROVIDERS",
    "check_domain_scope",
    "detect_prompt_injection",
    "get_chat_prompt_template",
    "get_embeddings",
    "get_llm",
    "get_rag_prompt_template",
    "sanitize_pii",
    "validate_embedding_dimension",
    "validate_input",
]
