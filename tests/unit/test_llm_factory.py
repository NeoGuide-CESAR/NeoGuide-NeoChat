"""Testes unitários para a fábrica de provedores de LLM e embeddings."""

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from lumi.core.config import Settings
from lumi.rag.llm_factory import (
    get_embeddings,
    get_llm,
    validate_embedding_dimension,
)


@pytest.fixture
def mock_settings() -> Settings:
    """Fixture com configurações de teste e chaves de API mockadas."""
    return Settings(
        default_llm_provider="gemini",
        default_embedding_provider="gemini",
        gemini_api_key="mock-gemini-api-key",
        gemini_model="gemini-1.5-pro",
        gemini_embedding_model="text-embedding-004",
        embedding_dimension=768,
        anthropic_api_key="mock-anthropic-api-key",
        anthropic_model="claude-3-5-sonnet-20241022",
    )


def test_get_llm_gemini(mock_settings: Settings) -> None:
    """Valida instanciação do provedor Gemini retornando ChatGoogleGenerativeAI configurado."""
    llm = get_llm(provider="gemini", settings=mock_settings)

    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model == "gemini-1.5-pro"
    # Valida chave de API mockada
    assert llm.google_api_key.get_secret_value() == "mock-gemini-api-key"


def test_get_llm_gemini_case_insensitive(mock_settings: Settings) -> None:
    """Valida que o nome do provedor é insensível a maiúsculas/minúsculas e espaços."""
    llm = get_llm(provider="  GEMINI  ", settings=mock_settings)
    assert isinstance(llm, ChatGoogleGenerativeAI)


def test_get_llm_claude_and_anthropic(mock_settings: Settings) -> None:
    """Valida instanciação do provedor Claude/Anthropic retornando ChatAnthropic configurado."""
    # Teste com alias 'claude'
    llm_claude = get_llm(provider="claude", settings=mock_settings)
    assert isinstance(llm_claude, ChatAnthropic)
    assert llm_claude.model == "claude-3-5-sonnet-20241022"
    assert llm_claude.anthropic_api_key.get_secret_value() == "mock-anthropic-api-key"

    # Teste com alias 'anthropic'
    llm_anthropic = get_llm(provider="anthropic", settings=mock_settings)
    assert isinstance(llm_anthropic, ChatAnthropic)
    assert llm_anthropic.model == "claude-3-5-sonnet-20241022"


def test_get_llm_invalid_provider(mock_settings: Settings) -> None:
    """Valida que provedor de LLM desconhecido lança ValueError explicativo."""
    with pytest.raises(ValueError, match="Provedor de LLM 'openai' não suportado"):
        get_llm(provider="openai", settings=mock_settings)


def test_get_llm_default_resolution(mock_settings: Settings) -> None:
    """Valida resolução do provedor padrão a partir de Settings.default_llm_provider."""
    # Padrão Gemini
    mock_settings.default_llm_provider = "gemini"
    llm = get_llm(settings=mock_settings)
    assert isinstance(llm, ChatGoogleGenerativeAI)

    # Padrão Claude
    mock_settings.default_llm_provider = "claude"
    llm_claude = get_llm(settings=mock_settings)
    assert isinstance(llm_claude, ChatAnthropic)


def test_get_llm_kwargs_forwarding(mock_settings: Settings) -> None:
    """Valida que parâmetros adicionais (kwargs) são repassados ao modelo."""
    llm = get_llm(provider="gemini", settings=mock_settings, temperature=0.3)
    assert llm.temperature == 0.3


def test_get_llm_missing_api_key() -> None:
    """Valida que a ausência da API Key levanta ValueError informativo."""
    settings_no_keys = Settings(
        gemini_api_key="",
        anthropic_api_key="",
    )
    with pytest.raises(ValueError, match="Chave de API do Google Gemini não configurada"):
        get_llm(provider="gemini", settings=settings_no_keys)

    with pytest.raises(ValueError, match="Chave de API do Anthropic Claude não configurada"):
        get_llm(provider="claude", settings=settings_no_keys)


def test_get_embeddings_gemini(mock_settings: Settings) -> None:
    """Valida instanciação de GoogleGenerativeAIEmbeddings com modelo e chave configurados."""
    embeddings = get_embeddings(provider="gemini", settings=mock_settings)

    assert isinstance(embeddings, GoogleGenerativeAIEmbeddings)
    assert embeddings.model == "text-embedding-004"
    assert embeddings.google_api_key.get_secret_value() == "mock-gemini-api-key"


def test_get_embeddings_fake(mock_settings: Settings) -> None:
    """Valida instanciação de FakeEmbeddings com dimensionalidade configurada (768)."""
    embeddings = get_embeddings(provider="fake", settings=mock_settings)

    assert isinstance(embeddings, FakeEmbeddings)
    assert embeddings.size == 768


def test_get_embeddings_default_resolution(mock_settings: Settings) -> None:
    """Valida resolução do provedor padrão a partir de Settings.default_embedding_provider."""
    mock_settings.default_embedding_provider = "fake"
    embeddings = get_embeddings(settings=mock_settings)
    assert isinstance(embeddings, FakeEmbeddings)
    assert embeddings.size == 768


def test_get_embeddings_invalid_provider(mock_settings: Settings) -> None:
    """Valida que provedor de embeddings inválido lança ValueError explicativo."""
    with pytest.raises(ValueError, match="Provedor de embeddings 'cohere' não suportado"):
        get_embeddings(provider="cohere", settings=mock_settings)


def test_get_embeddings_missing_api_key() -> None:
    """Valida que tentativa de criar embeddings Gemini sem chave de API levanta ValueError."""
    settings_no_keys = Settings(gemini_api_key="")
    with pytest.raises(ValueError, match="Chave de API do Google Gemini não configurada"):
        get_embeddings(provider="gemini", settings=settings_no_keys)


def test_validate_embedding_dimension(mock_settings: Settings) -> None:
    """Valida a verificação de dimensionalidade de embeddings (768 dimensões)."""
    valid_vector = [0.1] * 768
    invalid_vector = [0.1] * 512

    # Dimensão correta (768) retorna True
    assert validate_embedding_dimension(valid_vector, expected_dimension=768) is True
    assert validate_embedding_dimension(valid_vector, settings=mock_settings) is True

    # Dimensão incorreta deve lançar ValueError
    with pytest.raises(
        ValueError, match="Dimensão de embedding inválida: esperada 768, obtida 512"
    ):
        validate_embedding_dimension(invalid_vector, expected_dimension=768)
