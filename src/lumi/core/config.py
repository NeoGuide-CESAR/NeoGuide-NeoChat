"""Configurações centrais do sistema utilizando Pydantic Settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação Lumi NeoGuide."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API & Servidor
    environment: str = Field(default="development", description="Ambiente de execução")
    api_host: str = Field(default="0.0.0.0", description="Host da API")
    api_port: int = Field(default=8000, description="Porta da API")
    debug: bool = Field(default=True, description="Modo debug")
    log_level: str = Field(default="INFO", description="Nível de logging")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Origens permitidas para CORS",
    )
    api_key: str = Field(default="lumi-dev-secret-key", description="Chave de autenticação da API")

    # Banco de Dados & Vetores
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/lumi_db",
        description="URL de conexão assíncrona com PostgreSQL",
    )
    db_pool_size: int = Field(default=5, description="Tamanho do pool SQLAlchemy")
    db_max_overflow: int = Field(default=10, description="Overflow máximo do pool")
    db_pool_timeout: int = Field(default=30, description="Timeout de aquisição de conexão")

    # Provedores de IA
    default_llm_provider: str = Field(
        default="gemini", description="Provedor padrão de LLM (gemini ou claude/anthropic)"
    )
    default_embedding_provider: str = Field(
        default="gemini", description="Provedor padrão de embeddings (gemini ou fake)"
    )
    gemini_api_key: str = Field(default="", description="Chave de API do Google Gemini")
    gemini_model: str = Field(default="gemini-1.5-pro", description="Modelo LLM padrão")
    gemini_embedding_model: str = Field(
        default="text-embedding-004", description="Modelo de embedding vetorial"
    )
    embedding_dimension: int = Field(default=768, description="Dimensão do vetor de embedding")

    anthropic_api_key: str = Field(default="", description="Chave de API do Anthropic Claude")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022", description="Modelo Claude")

    # RAG
    similarity_threshold: float = Field(
        default=0.70, description="Threshold mínimo de similaridade de cosseno"
    )
    top_k_retrieval: int = Field(default=5, description="Número de chunks retornados no retrieval")
    reranker_enabled: bool = Field(default=False, description="Habilitar reranker cross-encoder")

    # Sessão e Limites
    session_ttl_hours: int = Field(default=1, description="TTL em horas para expiração de sessões")
    chat_history_limit: int = Field(
        default=10, description="Limite padrão de mensagens recentes na janela multi-turn"
    )
    rate_limit_requests_per_minute: int = Field(
        default=60, description="Limite de requisições por minuto por API Key"
    )


@lru_cache
def get_settings() -> Settings:
    """Retorna instância singleton cacheada das configurações."""
    return Settings()
