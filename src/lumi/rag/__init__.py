"""Módulo RAG (Retrieval-Augmented Generation) e IA Segura da Lumi."""

from lumi.rag.chains import RagContextOrchestrator
from lumi.rag.guardrails import (
    GuardrailResult,
    check_domain_scope,
    detect_prompt_injection,
    sanitize_pii,
    validate_input,
)
from lumi.rag.llm_factory import (
    DEFAULT_GEMINI_FALLBACK_MODELS,
    DEFAULT_GEMINI_PRIMARY_MODEL,
    MAX_FALLBACK_ATTEMPTS,
    SUPPORTED_EMBEDDING_PROVIDERS,
    SUPPORTED_LLM_PROVIDERS,
    get_embeddings,
    get_llm,
    get_llm_chain,
    get_model_name,
    validate_embedding_dimension,
)
from lumi.rag.output_guardrails import (
    OutputGuardrailResult,
    check_calculation_safeguard,
    extract_citations,
    validate_output,
)
from lumi.rag.prompts import (
    CONTINGENCY_NO_SOURCES_MESSAGE,
    CONTINGENCY_NO_SOURCES_PROMPT,
    LUMI_SYSTEM_PROMPT,
    get_chat_prompt_template,
    get_rag_prompt_template,
)
from lumi.rag.reranker import NormativeReranker
from lumi.rag.retriever import (
    NormativeRetriever,
    RetrievalResult,
    RetrievedChunk,
)
from lumi.rag.rewriter import QueryRewriter

__all__ = [
    "CONTINGENCY_NO_SOURCES_MESSAGE",
    "CONTINGENCY_NO_SOURCES_PROMPT",
    "DEFAULT_GEMINI_FALLBACK_MODELS",
    "DEFAULT_GEMINI_PRIMARY_MODEL",
    "GuardrailResult",
    "LUMI_SYSTEM_PROMPT",
    "MAX_FALLBACK_ATTEMPTS",
    "NormativeReranker",
    "NormativeRetriever",
    "OutputGuardrailResult",
    "QueryRewriter",
    "RagContextOrchestrator",
    "RetrievalResult",
    "RetrievedChunk",
    "SUPPORTED_EMBEDDING_PROVIDERS",
    "SUPPORTED_LLM_PROVIDERS",
    "check_calculation_safeguard",
    "check_domain_scope",
    "detect_prompt_injection",
    "extract_citations",
    "get_chat_prompt_template",
    "get_embeddings",
    "get_llm",
    "get_llm_chain",
    "get_model_name",
    "get_rag_prompt_template",
    "sanitize_pii",
    "validate_embedding_dimension",
    "validate_input",
    "validate_output",
]
