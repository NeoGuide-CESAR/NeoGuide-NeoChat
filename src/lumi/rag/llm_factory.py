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

DEFAULT_GEMINI_PRIMARY_MODEL: str = "gemini-3.8-flash"
DEFAULT_GEMINI_FAST_MODEL: str = "gemini-3.5-flash-lite"
DEFAULT_GEMINI_FALLBACK_MODELS: tuple[str, ...] = ("gemini-3.7-flash", "gemini-3.6-flash")
MAX_FALLBACK_ATTEMPTS: int = 3
_THINKING_BLOCK_TYPES: tuple[str, ...] = ("thinking", "reasoning")


def extract_text_content(content: Any) -> str:
    """Extrai o texto útil de respostas LLM em string simples ou lista de blocos Gemini 3+.

    Ignora blocos estruturados de raciocínio (`thinking` / `reasoning`) e extrai apenas o campo
    `text` de blocos de resposta ou strings diretas, evitando vazamento de dicionários crus ou
    falhas de parsing JSON.

    Args:
        content: Conteúdo bruto retornado em `response.content` ou `chunk.content`.

    Returns:
        str: Texto concatenado extraído, ou `""` quando `content` for `None`.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                block_type = block.get("type")
                if block_type in _THINKING_BLOCK_TYPES:
                    continue
                if "text" in block and block["text"] is not None:
                    parts.append(str(block["text"]))
        return "".join(parts)
    return str(content)


def _is_gemini_3_or_newer(model_name: str) -> bool:
    """Verifica se o identificador de modelo pertence à família Gemini 3+."""
    return model_name.strip().lower().startswith("gemini-3")


def get_model_name(model: Any) -> str:
    """Extrai o nome ou identificador de modelo de uma instância de chat model ou mock.

    Args:
        model: Objeto do modelo (BaseChatModel ou mock com atributo model, model_name ou name).

    Returns:
        str: Identificador do modelo ou "unknown_model".
    """
    for attr in ("model", "model_name", "name"):
        val = getattr(model, attr, None)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return "unknown_model"


def _build_llm(
    provider: str | None = None,
    settings: Settings | None = None,
    *,
    use_fast_model: bool = False,
    **kwargs: Any,
) -> BaseChatModel:
    """Constrói uma instância de LLM parametrizada para perfil padrão ou rápido."""
    resolved_settings = settings or get_settings()
    selected_provider = (provider or resolved_settings.default_llm_provider).strip().lower()

    if selected_provider == "gemini":
        api_key = resolved_settings.gemini_api_key
        if not api_key:
            raise ValueError(
                "Chave de API do Google Gemini não configurada. Defina GEMINI_API_KEY no ambiente."
            )
        default_model = (
            resolved_settings.gemini_fast_model
            if use_fast_model
            else resolved_settings.gemini_model
        )
        model_name = kwargs.pop("model", default_model)

        has_explicit_thinking = "thinking_level" in kwargs or "reasoning_effort" in kwargs
        if not has_explicit_thinking and _is_gemini_3_or_newer(model_name):
            configured_thinking = (
                resolved_settings.gemini_fast_thinking_level
                if use_fast_model
                else resolved_settings.gemini_thinking_level
            )
            if configured_thinking is not None:
                kwargs["thinking_level"] = configured_thinking

        # Falha rápida no SDK para que erros 503/timeout acionem imediatamente a cadeia de fallback
        kwargs.setdefault("max_retries", resolved_settings.gemini_max_retries)
        if resolved_settings.gemini_timeout is not None:
            kwargs.setdefault("timeout", resolved_settings.gemini_timeout)

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


def _build_llm_chain(
    provider: str | None = None,
    settings: Settings | None = None,
    *,
    use_fast_model: bool = False,
    **kwargs: Any,
) -> list[BaseChatModel]:
    """Constrói a cadeia ordenada de instâncias de LLM (primário e fallbacks)."""
    resolved_settings = settings or get_settings()
    selected_provider = (provider or resolved_settings.default_llm_provider).strip().lower()

    if selected_provider == "gemini":
        if use_fast_model:
            model_names: list[str] = [resolved_settings.gemini_fast_model]
            if resolved_settings.gemini_model not in model_names:
                model_names.append(resolved_settings.gemini_model)
        else:
            model_names = [resolved_settings.gemini_model]

        for fb in getattr(resolved_settings, "gemini_fallback_models", []):
            if fb not in model_names:
                model_names.append(fb)

        # Limite estrito de MAX_FALLBACK_ATTEMPTS (3)
        model_names = model_names[:MAX_FALLBACK_ATTEMPTS]

        chain: list[BaseChatModel] = []
        for m_name in model_names:
            model_kwargs = dict(kwargs)
            model_kwargs["model"] = m_name
            chain.append(
                _build_llm(
                    provider="gemini",
                    settings=resolved_settings,
                    use_fast_model=use_fast_model,
                    **model_kwargs,
                )
            )
        return chain

    # Para outros provedores, retorna lista com o modelo principal configurado
    return [
        _build_llm(
            provider=selected_provider,
            settings=resolved_settings,
            use_fast_model=use_fast_model,
            **kwargs,
        )
    ]


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
    return _build_llm(provider=provider, settings=settings, use_fast_model=False, **kwargs)


def get_fast_llm(
    provider: str | None = None,
    settings: Settings | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Retorna uma instância de LLM rápida para etapas auxiliares (reranker e reescrita).

    Para o provedor Gemini, utiliza `settings.gemini_fast_model` e
    `settings.gemini_fast_thinking_level`. Para outros provedores, mantém o comportamento de `get_llm`.
    """
    return _build_llm(provider=provider, settings=settings, use_fast_model=True, **kwargs)


def get_llm_chain(
    provider: str | None = None,
    settings: Settings | None = None,
    **kwargs: Any,
) -> list[BaseChatModel]:
    """Retorna uma cadeia ordenada de instâncias de LLM (primário e fallbacks) para o provedor.

    Para o provedor Gemini, instancia sequencialmente o modelo primário e os modelos de fallback
    configurados até o limite estrito de MAX_FALLBACK_ATTEMPTS (3).

    Args:
        provider: Nome do provedor ("gemini", "claude" ou "anthropic").
        settings: Objeto de configurações do sistema (opcional).
        **kwargs: Parâmetros repassados ao construtor de cada modelo (ex.: temperature).

    Returns:
        list[BaseChatModel]: Lista contendo o modelo primário e modelos de fallback.
    """
    return _build_llm_chain(provider=provider, settings=settings, use_fast_model=False, **kwargs)


def get_fast_llm_chain(
    provider: str | None = None,
    settings: Settings | None = None,
    **kwargs: Any,
) -> list[BaseChatModel]:
    """Retorna a cadeia ordenada de instâncias rápidas de LLM para etapas auxiliares do RAG.

    Para o provedor Gemini, prioriza `settings.gemini_fast_model` seguido de `gemini_model` e
    `gemini_fallback_models` até o limite de `MAX_FALLBACK_ATTEMPTS`.
    """
    return _build_llm_chain(provider=provider, settings=settings, use_fast_model=True, **kwargs)


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
    "DEFAULT_GEMINI_FALLBACK_MODELS",
    "DEFAULT_GEMINI_FAST_MODEL",
    "DEFAULT_GEMINI_PRIMARY_MODEL",
    "MAX_FALLBACK_ATTEMPTS",
    "SUPPORTED_EMBEDDING_PROVIDERS",
    "SUPPORTED_LLM_PROVIDERS",
    "extract_text_content",
    "get_embeddings",
    "get_fast_llm",
    "get_fast_llm_chain",
    "get_llm",
    "get_llm_chain",
    "get_model_name",
    "validate_embedding_dimension",
]
