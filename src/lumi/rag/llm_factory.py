"""Fábrica de provedores de LLM e embeddings desacoplada."""

from collections.abc import Sequence
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.embeddings import Embeddings
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from lumi.core.config import Settings, get_settings

SUPPORTED_LLM_PROVIDERS: tuple[str, ...] = ("gemini", "claude", "anthropic")
SUPPORTED_EMBEDDING_PROVIDERS: tuple[str, ...] = ("gemini", "fake")


def get_llm(
    provider: str | None = None,
    settings: Settings | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Retorna uma instância de modelo de linguagem (LLM) baseado no provedor configurado.

    Args:
        provider: Nome do provedor ("gemini", "claude" ou "anthropic").
                  Se omitido, utiliza `settings.default_llm_provider`.
        settings: Objeto de configurações do sistema (opcional, utiliza singleton padrão).
        **kwargs: Parâmetros adicionais repassados ao construtor do modelo (ex.: temperature).

    Returns:
        BaseChatModel: Instância do modelo de chat LangChain (ChatGoogleGenerativeAI ou ChatAnthropic).

    Raises:
        ValueError: Caso o provedor não seja suportado ou falte a chave de API obrigatória.
    """
    resolved_settings = settings or get_settings()
    selected_provider = (provider or resolved_settings.default_llm_provider).strip().lower()

    if selected_provider == "gemini":
        api_key = resolved_settings.gemini_api_key
        if not api_key:
            raise ValueError(
                "Chave de API do Google Gemini não configurada. Defina GEMINI_API_KEY no ambiente."
            )
        model_name = kwargs.pop("model", resolved_settings.gemini_model)
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            **kwargs,
        )

    if selected_provider in ("claude", "anthropic"):
        api_key = resolved_settings.anthropic_api_key
        if not api_key:
            raise ValueError(
                "Chave de API do Anthropic Claude não configurada. Defina ANTHROPIC_API_KEY no ambiente."
            )
        model_name = kwargs.pop("model", resolved_settings.anthropic_model)
        return ChatAnthropic(
            model=model_name,
            api_key=api_key,
            **kwargs,
        )

    raise ValueError(
        f"Provedor de LLM '{selected_provider}' não suportado. "
        f"Provedores válidos: {', '.join(repr(p) for p in SUPPORTED_LLM_PROVIDERS)}."
    )


def get_embeddings(
    provider: str | None = None,
    settings: Settings | None = None,
    **kwargs: Any,
) -> Embeddings:
    """Retorna uma instância de gerador de embeddings baseada no provedor configurado.

    Args:
        provider: Nome do provedor ("gemini" ou "fake").
                  Se omitido, utiliza `settings.default_embedding_provider`.
        settings: Objeto de configurações do sistema (opcional, utiliza singleton padrão).
        **kwargs: Parâmetros adicionais repassados ao construtor do embedding.

    Returns:
        Embeddings: Instância de embeddings LangChain (GoogleGenerativeAIEmbeddings ou FakeEmbeddings).

    Raises:
        ValueError: Caso o provedor não seja suportado ou falte a chave de API obrigatória.
    """
    resolved_settings = settings or get_settings()
    selected_provider = (provider or resolved_settings.default_embedding_provider).strip().lower()

    if selected_provider == "gemini":
        api_key = resolved_settings.gemini_api_key
        if not api_key:
            raise ValueError(
                "Chave de API do Google Gemini não configurada. Defina GEMINI_API_KEY no ambiente."
            )
        model_name = kwargs.pop("model", resolved_settings.gemini_embedding_model)
        kwargs.setdefault("output_dimensionality", resolved_settings.embedding_dimension)
        return GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=api_key,
            **kwargs,
        )

    if selected_provider == "fake":
        size = kwargs.pop("size", resolved_settings.embedding_dimension)
        try:
            import numpy as _np  # noqa: F401

            return FakeEmbeddings(size=size, **kwargs)
        except ImportError:

            class _SafeFakeEmbeddings(FakeEmbeddings):
                def _get_embedding(self) -> list[float]:
                    return [0.1] * self.size

            return _SafeFakeEmbeddings(size=size, **kwargs)

    raise ValueError(
        f"Provedor de embeddings '{selected_provider}' não suportado. "
        f"Provedores válidos: {', '.join(repr(p) for p in SUPPORTED_EMBEDDING_PROVIDERS)}."
    )


def validate_embedding_dimension(
    embedding: Sequence[float],
    expected_dimension: int | None = None,
    settings: Settings | None = None,
) -> bool:
    """Valida se o vetor de embedding possui a dimensionalidade correta requerida pelo pgvector.

    Args:
        embedding: Sequência contendo as coordenadas do vetor gerado.
        expected_dimension: Dimensão esperada (opcional, padrão derivado de Settings.embedding_dimension).
        settings: Configurações do sistema (opcional).

    Returns:
        bool: True se a dimensão for compatível.

    Raises:
        ValueError: Caso a dimensão do vetor seja diferente da dimensão esperada.
    """
    resolved_settings = settings or get_settings()
    expected = expected_dimension or resolved_settings.embedding_dimension
    actual = len(embedding)

    if actual != expected:
        raise ValueError(f"Dimensão de embedding inválida: esperada {expected}, obtida {actual}.")

    return True


__all__ = [
    "SUPPORTED_EMBEDDING_PROVIDERS",
    "SUPPORTED_LLM_PROVIDERS",
    "get_embeddings",
    "get_llm",
    "validate_embedding_dimension",
]
