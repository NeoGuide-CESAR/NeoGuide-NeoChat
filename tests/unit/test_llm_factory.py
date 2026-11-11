"""Testes unitários para a fábrica de provedores de LLM e embeddings."""

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.embeddings.fake import FakeEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from lumi.core.config import Settings
from lumi.rag.llm_factory import (
    extract_text_content,
    get_embeddings,
    get_fast_llm,
    get_fast_llm_chain,
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


def test_settings_fast_model_and_thinking_defaults() -> None:
    """Valida defaults de modelo rápido e thinking_level em Settings."""
    settings = Settings(_env_file=None)
    assert settings.gemini_fast_model == "gemini-3.5-flash-lite"
    assert settings.gemini_thinking_level == "low"
    assert settings.gemini_fast_thinking_level is None


def test_get_llm_applies_thinking_level_only_on_gemini_3_plus() -> None:
    """Aplica thinking_level apenas para família Gemini 3+, preservando modelos legados."""
    settings_v3 = Settings(
        _env_file=None,
        gemini_api_key="mock-gemini-api-key",
        gemini_model="gemini-3.8-flash",
        gemini_thinking_level="low",
    )
    llm_v3 = get_llm(provider="gemini", settings=settings_v3)
    assert isinstance(llm_v3, ChatGoogleGenerativeAI)
    assert llm_v3.model == "gemini-3.8-flash"
    assert llm_v3.reasoning_effort == "low"

    # Override explícito via kwargs deve prevalecer
    llm_v3_high = get_llm(provider="gemini", settings=settings_v3, thinking_level="high")
    assert llm_v3_high.reasoning_effort == "high"

    # Modelo legado Gemini 1.5 não deve receber thinking_level
    settings_v1 = Settings(
        _env_file=None,
        gemini_api_key="mock-gemini-api-key",
        gemini_model="gemini-1.5-pro",
        gemini_thinking_level="low",
    )
    llm_v1 = get_llm(provider="gemini", settings=settings_v1)
    assert llm_v1.model == "gemini-1.5-pro"
    assert llm_v1.reasoning_effort is None


def test_get_fast_llm_and_chain_gemini() -> None:
    """Valida get_fast_llm e get_fast_llm_chain usando gemini-3.5-flash-lite e fast thinking."""
    settings = Settings(
        _env_file=None,
        gemini_api_key="mock-gemini-api-key",
        anthropic_api_key="mock-anthropic-api-key",
    )
    fast_llm = get_fast_llm(provider="gemini", settings=settings)
    assert isinstance(fast_llm, ChatGoogleGenerativeAI)
    assert fast_llm.model == "gemini-3.5-flash-lite"
    assert fast_llm.reasoning_effort is None

    settings_with_fast_thinking = Settings(
        _env_file=None,
        gemini_api_key="mock-gemini-api-key",
        gemini_fast_thinking_level="minimal",
    )
    fast_llm_min = get_fast_llm(provider="gemini", settings=settings_with_fast_thinking)
    assert fast_llm_min.reasoning_effort == "minimal"

    fast_chain = get_fast_llm_chain(provider="gemini", settings=settings)
    assert [m.model for m in fast_chain] == [
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
    ]

    # Claude mantém o comportamento padrão
    fast_claude = get_fast_llm(provider="claude", settings=settings)
    assert isinstance(fast_claude, ChatAnthropic)
    assert fast_claude.model == settings.anthropic_model


def test_extract_text_content_edge_cases() -> None:
    """Valida extração de texto em strings, None e blocos estruturados Gemini 3+."""
    assert extract_text_content(None) == ""
    assert extract_text_content("Resposta simples") == "Resposta simples"
    assert extract_text_content(42) == "42"

    # Lista com bloco text + signature extras
    blocks_with_signature = [
        {
            "type": "text",
            "text": "[2, 0, 1]",
            "extras": {"signature": "sig-abc-123"},
        }
    ]
    assert extract_text_content(blocks_with_signature) == "[2, 0, 1]"

    # Lista com bloco thinking + reasoning + text + string solta
    mixed_blocks = [
        {"type": "thinking", "thinking": "Analisando [9, 9] internamente..."},
        {"type": "reasoning", "text": "Raciocínio oculto que não deve vazar"},
        {"type": "text", "text": "Conforme a norma "},
        "DIS-NOR-030",
        {"text": ", o limite é 5%."},
    ]
    assert extract_text_content(mixed_blocks) == "Conforme a norma DIS-NOR-030, o limite é 5%."
