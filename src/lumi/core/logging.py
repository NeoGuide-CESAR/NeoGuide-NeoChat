"""Configuração centralizada de logging estruturado utilizando structlog."""

import logging
import sys
from collections.abc import Mapping
from typing import Any, cast

import structlog
from structlog.types import EventDict, Processor

from lumi.core.config import get_settings

# Chaves sensíveis que devem ser mascaradas recursivamente
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "x-api-key",
        "authorization",
        "password",
        "token",
        "secret",
        "access_token",
        "cookie",
    }
)


def _is_sensitive(key: str) -> bool:
    """Verifica se uma chave corresponde a termos sensíveis (case-insensitive)."""
    k = key.lower()
    return (
        k in SENSITIVE_KEYS
        or k.replace("-", "_") in SENSITIVE_KEYS
        or k.replace("_", "-") in SENSITIVE_KEYS
    )


def _redact_data(data: Any) -> Any:
    """Aplica mascaramento recursivo de forma defensiva em dicts, lists e tuples."""
    if isinstance(data, Mapping):
        redacted: dict[str, Any] = {}
        for k, v in data.items():
            if isinstance(k, str) and _is_sensitive(k):
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = _redact_data(v)
        return redacted
    elif isinstance(data, list):
        return [_redact_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(_redact_data(item) for item in data)
    return data


def redact_sensitive_data(
    logger: Any,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Processador do structlog para mascarar dados sensíveis."""
    return cast(EventDict, _redact_data(event_dict))


def setup_logging(
    environment: str | None = None,
    log_level: str | None = None,
) -> None:
    """Configura o logging centralizado do structlog e unifica com a stdlib."""
    settings = get_settings()
    env = environment or settings.environment
    level_str = log_level or settings.log_level
    numeric_level = getattr(logging, level_str.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        redact_sensitive_data,
    ]

    renderer: Processor
    if env in ("production", "staging"):
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(numeric_level)

    # Unificação com loggers de bibliotecas essenciais
    stdlib_loggers = ("uvicorn", "uvicorn.access", "uvicorn.error", "sqlalchemy.engine")
    for logger_name in stdlib_loggers:
        lib_logger = logging.getLogger(logger_name)
        lib_logger.handlers = [handler]
        lib_logger.propagate = False
        lib_logger.setLevel(numeric_level)
