"""Testes unitários e de integração para logging estruturado e correlation middleware."""

import io
import json
import logging
import uuid
from typing import Any
from unittest.mock import patch

import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from lumi.api.middleware import CorrelationIdMiddleware
from lumi.core.config import Settings
from lumi.core.logging import (
    SENSITIVE_KEYS,
    redact_sensitive_data,
    setup_logging,
)
from lumi.main import app as main_app


class TestRedactSensitiveData:
    """Testes unitários para o processador defensivo de mascaramento."""

    def test_sensitive_keys_constant(self) -> None:
        """Verifica se todas as chaves obrigatórias constam na definição."""
        required = {
            "api_key",
            "x-api-key",
            "authorization",
            "password",
            "token",
            "secret",
            "access_token",
            "cookie",
        }
        assert required.issubset(SENSITIVE_KEYS)

    def test_redacts_direct_keys_case_insensitive(self) -> None:
        """Testa redaction de chaves sensíveis em minúsculas e maiúsculas."""
        event_dict: dict[str, Any] = {
            "api_key": "secret-123",
            "X-API-KEY": "secret-456",
            "Authorization": "Bearer tok",
            "password": "pass",
            "TOKEN": "jwt-token",
            "Secret": "super-secret",
            "access_token": "acc-tok",
            "Cookie": "session=abc",
            "safe_field": "public_value",
            "user_id": 42,
        }
        redacted = redact_sensitive_data(None, "info", event_dict)

        for key in [
            "api_key",
            "X-API-KEY",
            "Authorization",
            "password",
            "TOKEN",
            "Secret",
            "access_token",
            "Cookie",
        ]:
            assert redacted[key] == "[REDACTED]"

        assert redacted["safe_field"] == "public_value"
        assert redacted["user_id"] == 42

    def test_redacts_nested_structures(self) -> None:
        """Testa mascaramento recursivo em dicionários e listas aninhadas."""
        event_dict: dict[str, Any] = {
            "headers": {
                "Authorization": "Bearer secret-token",
                "Content-Type": "application/json",
            },
            "payload": {
                "users": [
                    {"name": "Alice", "password": "123"},
                    {"name": "Bob", "secret": "abc"},
                ],
                "tokens": ["tok1", "tok2"],
            },
            "meta": {
                "nested_token": {
                    "token": "inner-token",
                }
            },
        }
        redacted = redact_sensitive_data(None, "info", event_dict)

        assert redacted["headers"]["Authorization"] == "[REDACTED]"
        assert redacted["headers"]["Content-Type"] == "application/json"
        assert redacted["payload"]["users"][0]["password"] == "[REDACTED]"
        assert redacted["payload"]["users"][0]["name"] == "Alice"
        assert redacted["payload"]["users"][1]["secret"] == "[REDACTED]"
        assert redacted["meta"]["nested_token"]["token"] == "[REDACTED]"

    def test_handles_non_dict_event_dict_safely(self) -> None:
        """Testa comportamento defensivo com estruturas diversas."""
        event_dict: dict[str, Any] = {"event": "simple_message"}
        redacted = redact_sensitive_data(None, "info", event_dict)
        assert redacted == {"event": "simple_message"}


class TestSetupLogging:
    """Testes para a função central setup_logging."""

    def test_setup_logging_defaults_from_settings(self) -> None:
        """Garante que setup_logging lê valores padrão de get_settings()."""
        mock_settings = Settings(environment="development", log_level="DEBUG")
        with patch("lumi.core.logging.get_settings", return_value=mock_settings):
            setup_logging()
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

    def test_setup_logging_explicit_parameters(self) -> None:
        """Testa parametrização explícita sobrepondo get_settings()."""
        setup_logging(environment="staging", log_level="WARNING")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_setup_logging_json_renderer_production(self) -> None:
        """Valida que produção utiliza JSONRenderer."""
        log_stream = io.StringIO()
        with patch("sys.stdout", log_stream):
            setup_logging(environment="production", log_level="INFO")
            logger = structlog.get_logger("test_prod_logger")
            logger.info("evento_producao", servico="lumi", api_key="secret")

        output = log_stream.getvalue()
        assert output.strip() != ""
        parsed = json.loads(output.strip().splitlines()[-1])
        assert parsed["event"] == "evento_producao"
        assert parsed["servico"] == "lumi"
        assert parsed["api_key"] == "[REDACTED]"
        assert "timestamp" in parsed
        assert parsed["level"] == "info"

    def test_setup_logging_console_renderer_development(self) -> None:
        """Valida que desenvolvimento utiliza ConsoleRenderer."""
        log_stream = io.StringIO()
        with patch("sys.stdout", log_stream):
            setup_logging(environment="development", log_level="INFO")
            logger = structlog.get_logger("test_dev_logger")
            logger.info("evento_dev", modulo="core")

        output = log_stream.getvalue()
        assert "evento_dev" in output
        assert "modulo=core" in output or "modulo" in output

    def test_stdlib_loggers_unified(self) -> None:
        """Valida que loggers da standard library são canalizados com mesmo formato."""
        log_stream = io.StringIO()
        with patch("sys.stdout", log_stream):
            setup_logging(environment="production", log_level="INFO")
            uvicorn_log = logging.getLogger("uvicorn.access")
            uvicorn_log.info("GET /health 200 OK")

        output = log_stream.getvalue()
        assert output.strip() != ""
        parsed = json.loads(output.strip().splitlines()[-1])
        assert "GET /health 200 OK" in parsed["event"]


class TestCorrelationIdMiddleware:
    """Testes unitários para o CorrelationIdMiddleware."""

    def test_generates_uuid_when_header_missing(self) -> None:
        """Gera um UUIDv4 válido quando X-Request-ID não for fornecido."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        async def sample_endpoint() -> dict[str, str]:
            # Verifica que foi vinculado às contextvars durante a execução
            context_dict = structlog.contextvars.get_contextvars()
            return {"request_id": context_dict.get("request_id", "")}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        generated_id = response.headers.get("X-Request-ID")
        assert generated_id is not None
        # Valida formato UUID
        uuid.UUID(generated_id)
        assert response.json()["request_id"] == generated_id

    def test_preserves_existing_request_id_header(self) -> None:
        """Preserva o X-Request-ID customizado passado pelo chamador."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        async def sample_endpoint() -> dict[str, str]:
            context_dict = structlog.contextvars.get_contextvars()
            return {"request_id": context_dict.get("request_id", "")}

        client = TestClient(app)
        custom_id = "meu-custom-request-id-999"
        response = client.get("/test", headers={"X-Request-ID": custom_id})

        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == custom_id
        assert response.json()["request_id"] == custom_id

    def test_clears_contextvars_after_request(self) -> None:
        """Garante que contextvars são limpas no bloco finally."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        async def sample_endpoint() -> dict[str, str]:
            return {"ok": "true"}

        client = TestClient(app)
        client.get("/test")

        # Após a requisição terminar, contextvars não devem reter request_id
        context_dict = structlog.contextvars.get_contextvars()
        assert "request_id" not in context_dict

    def test_clears_contextvars_even_on_exception(self) -> None:
        """Garante que contextvars são limpas mesmo se a rota disparar exceção."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/error")
        async def error_endpoint() -> JSONResponse:
            raise RuntimeError("Erro intencional para teste")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/error")
        assert response.status_code == 500

        context_dict = structlog.contextvars.get_contextvars()
        assert "request_id" not in context_dict

    def test_logs_request_lifecycle_with_metrics(self) -> None:
        """Verifica se início e fim da requisição são registrados com métricas."""
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/ping")
        async def ping() -> dict[str, str]:
            return {"status": "pong"}

        captured_events: list[dict[str, Any]] = []

        def capture_processor(
            logger: Any, method_name: str, event_dict: dict[str, Any]
        ) -> dict[str, Any]:
            captured_events.append(dict(event_dict))
            return event_dict

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                capture_processor,
                structlog.processors.JSONRenderer(),
            ]
        )

        client = TestClient(app)
        response = client.get("/ping", headers={"X-Request-ID": "test-tracking-123"})
        assert response.status_code == 200

        # Procura eventos de início e fim
        started_events = [e for e in captured_events if e.get("event") == "request_started"]
        finished_events = [e for e in captured_events if e.get("event") == "request_finished"]

        assert len(started_events) >= 1
        assert started_events[0]["method"] == "GET"
        assert started_events[0]["path"] == "/ping"
        assert started_events[0]["request_id"] == "test-tracking-123"

        assert len(finished_events) >= 1
        assert finished_events[0]["method"] == "GET"
        assert finished_events[0]["path"] == "/ping"
        assert finished_events[0]["status_code"] == 200
        assert "duration_ms" in finished_events[0]
        assert isinstance(finished_events[0]["duration_ms"], (int, float))
        assert finished_events[0]["request_id"] == "test-tracking-123"


class TestMainAppIntegration:
    """Testes de integração com a instância principal app em lumi.main."""

    def test_main_app_returns_request_id_header(self) -> None:
        """Verifica se requisições para main_app retornam X-Request-ID."""
        client = TestClient(main_app)
        response = client.get("/health")
        assert response.status_code == 200
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None
        uuid.UUID(request_id)

    def test_main_app_preserves_custom_request_id(self) -> None:
        """Verifica se main_app propaga o X-Request-ID enviado."""
        client = TestClient(main_app)
        custom_id = "uuid-externo-client-777"
        response = client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == custom_id
