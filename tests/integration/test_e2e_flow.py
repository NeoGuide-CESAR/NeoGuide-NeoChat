"""Testes de integração ponta a ponta (E2E) para a jornada completa do Lumi NeoGuide."""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from langchain_core.messages import AIMessageChunk
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.api.deps import get_db, get_db_session
from lumi.core.config import get_settings
from lumi.db.models import ChatMessage, ChatSession
from lumi.main import app
from lumi.rag.chains import RagContextOrchestrator
from lumi.rag.retriever import RetrievalResult, RetrievedChunk


class InMemoryDatabaseState:
    """Simulador de banco de dados em memória para testes E2E com persistência de sessões e mensagens."""

    def __init__(self) -> None:
        self.sessions: dict[UUID, ChatSession] = {}
        self.messages: dict[UUID, list[ChatMessage]] = {}
        self.analytics_records: list[dict[str, Any]] = []

    def create_mock_session(self) -> AsyncMock:
        mock = AsyncMock(spec=AsyncSession)

        def _add(instance: Any) -> None:
            if isinstance(instance, ChatSession):
                self.sessions[instance.id] = instance
            elif isinstance(instance, ChatMessage):
                self.messages.setdefault(instance.session_id, []).append(instance)

        mock.add = MagicMock(side_effect=_add)
        mock.flush = AsyncMock()
        mock.commit = AsyncMock()

        def _execute(stmt: Any, *args: Any, **kwargs: Any) -> MagicMock:
            stmt_str = str(stmt).lower()
            res = MagicMock()

            if "chat_messages" in stmt_str or "chatmessage" in stmt_str:
                # Retorna todas as mensagens do histórico da sessão
                all_msgs: list[ChatMessage] = []
                for msgs in self.messages.values():
                    all_msgs.extend(msgs)
                res.scalars.return_value.all.return_value = all_msgs
                return res

            if "chat_sessions" in stmt_str or "chatsession" in stmt_str:
                # Retorna a sessão correspondente se encontrada
                found_session: ChatSession | None = None
                for s in self.sessions.values():
                    found_session = s
                    break
                res.scalar_one_or_none.return_value = found_session
                return res

            res.scalar_one_or_none.return_value = None
            res.scalars.return_value.all.return_value = []
            return res

        mock.execute.side_effect = _execute
        return mock


@pytest.fixture
def e2e_state() -> InMemoryDatabaseState:
    return InMemoryDatabaseState()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    settings = get_settings()
    return {"X-API-Key": settings.api_key}


@pytest.mark.integration
class TestEndToEndFlow:
    """Valida o fluxo ponta a ponta: /health, criação de sessão, stream SSE, multi-turn, telemetria e TTL."""

    @pytest.mark.asyncio
    async def test_complete_e2e_conversational_flow(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        e2e_state: InMemoryDatabaseState,
    ) -> None:
        """Executa a esteira E2E completa simulando a jornada real de um usuário técnico."""
        # -------------------------------------------------------------
        # 1. Health Check do Serviço
        # -------------------------------------------------------------
        health_resp = await async_client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "healthy"
        assert "version" in health_data

        # -------------------------------------------------------------
        # 2. Criação de Nova Sessão
        # -------------------------------------------------------------
        mock_db = e2e_state.create_mock_session()

        async def _override_db():
            yield mock_db

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_db_session] = _override_db

        try:
            session_resp = await async_client.post("/api/v1/sessions", headers=auth_headers)
            assert session_resp.status_code == 201
            session_data = session_resp.json()
            session_id_str = session_data["id"]
            session_id = UUID(session_id_str)
            assert session_id in e2e_state.sessions

            # -------------------------------------------------------------
            # 3. Primeiro Turno: Pergunta com Streaming SSE (/api/v1/chat)
            # -------------------------------------------------------------
            chunk_doc30 = RetrievedChunk(
                chunk_id=uuid4(),
                document_code="DIS-NOR-030",
                document_title="Norma de Redes Aéreas",
                revision="REV07",
                section_code="Item 4.1",
                section_title="Distâncias Mínimas",
                page_number=15,
                content="A distância mínima vertical de segurança para condutores é 5,5 metros.",
                similarity_score=0.94,
                metadata={"table": False},
            )
            mock_rag_result = RetrievalResult(
                query="qual a distância mínima de segurança?",
                chunks=[chunk_doc30],
                is_contingency=False,
            )

            mock_orchestrator = AsyncMock(spec=RagContextOrchestrator)
            mock_orchestrator.get_context.return_value = mock_rag_result

            mock_llm_stream = MagicMock()

            async def _stream_tokens(
                *args: Any, **kwargs: Any
            ) -> AsyncGenerator[AIMessageChunk, None]:
                yield AIMessageChunk(content="De acordo com a DIS-NOR-030, ")
                yield AIMessageChunk(content="a distância vertical de segurança é 5,5m.")

            mock_llm_stream.astream = _stream_tokens

            mock_persist = AsyncMock(return_value=True)

            with (
                patch("lumi.services.chat_service.get_llm", return_value=mock_llm_stream),
                patch(
                    "lumi.services.chat_service.create_rag_orchestrator",
                    return_value=mock_orchestrator,
                ),
                patch(
                    "lumi.api.v1.chat.ChatService",
                    side_effect=lambda *args, **kwargs: __import__(
                        "lumi.services.chat_service", fromlist=["ChatService"]
                    ).ChatService(*args, **{**kwargs, "persist_interaction_fn": mock_persist}),
                ),
            ):
                chat_payload = {
                    "session_id": session_id_str,
                    "message": "Qual é a distância mínima de segurança para condutores?",
                    "stream": True,
                }

                sse_resp = await async_client.post(
                    "/api/v1/chat", json=chat_payload, headers=auth_headers
                )
                assert sse_resp.status_code == 200
                assert "text/event-stream" in sse_resp.headers["content-type"]

                # Parse dos eventos SSE por bloco delimitado por \n\n
                blocks = [b.strip() for b in sse_resp.text.strip().split("\n\n") if b.strip()]
                parsed_events: list[tuple[str | None, dict[str, Any]]] = []
                for block in blocks:
                    event_type = None
                    data_dict: dict[str, Any] = {}
                    for line in block.split("\n"):
                        if line.startswith("event: "):
                            event_type = line[7:].strip()
                        elif line.startswith("data: "):
                            data_dict = json.loads(line[6:].strip())
                    parsed_events.append((event_type, data_dict))

                # Valida eventos de token
                token_contents = [
                    data["token"] for ev, data in parsed_events if ev == "token" and "token" in data
                ]
                full_stream_text = "".join(token_contents)
                assert "5,5m" in full_stream_text

                # Verifica evento de fontes
                source_events = [data for ev, data in parsed_events if ev == "sources"]
                assert len(source_events) >= 1
                assert source_events[0]["sources"][0]["document_code"] == "DIS-NOR-030"

                # Verifica evento done
                done_events = [data for ev, data in parsed_events if ev == "done"]
                assert len(done_events) == 1
                assert done_events[0]["session_id"] == session_id_str

                # Verifica persistência assíncrona de telemetria
                mock_persist.assert_awaited_once()
                call_kwargs = mock_persist.call_args.kwargs
                assert call_kwargs["session_id"] == session_id
                assert call_kwargs["top_document_code"] == "DIS-NOR-030"
                assert call_kwargs["top_similarity_score"] == 0.94
                assert call_kwargs["latency_ms"] >= 0

            # Registra mensagens do primeiro turno no histórico da sessão
            now = datetime.now(UTC)
            e2e_state.messages[session_id] = [
                ChatMessage(
                    id=uuid4(),
                    session_id=session_id,
                    role="user",
                    content="Qual é a distância mínima de segurança para condutores?",
                    created_at=now - timedelta(seconds=5),
                ),
                ChatMessage(
                    id=uuid4(),
                    session_id=session_id,
                    role="assistant",
                    content="De acordo com a DIS-NOR-030, a distância vertical é 5,5m.",
                    sources=[{"document_code": "DIS-NOR-030", "page_number": 15}],
                    created_at=now,
                ),
            ]

            # -------------------------------------------------------------
            # 4. Segundo Turno: Pergunta Multi-turn Contextual (stream=False)
            # -------------------------------------------------------------
            mock_llm_sync = MagicMock()
            mock_llm_sync.ainvoke = AsyncMock(
                return_value=MagicMock(
                    content="Em travessias sobre rodovias, a distância eleva-se para 6,0 metros."
                )
            )

            mock_persist_turn2 = AsyncMock(return_value=True)

            with (
                patch("lumi.services.chat_service.get_llm", return_value=mock_llm_sync),
                patch(
                    "lumi.services.chat_service.create_rag_orchestrator",
                    return_value=mock_orchestrator,
                ),
                patch(
                    "lumi.api.v1.chat.ChatService",
                    side_effect=lambda *args, **kwargs: __import__(
                        "lumi.services.chat_service", fromlist=["ChatService"]
                    ).ChatService(
                        *args, **{**kwargs, "persist_interaction_fn": mock_persist_turn2}
                    ),
                ),
            ):
                turn2_payload = {
                    "session_id": session_id_str,
                    "message": "E em caso de travessia rodoviária?",
                    "stream": False,
                }

                sync_resp = await async_client.post(
                    "/api/v1/chat", json=turn2_payload, headers=auth_headers
                )
                assert sync_resp.status_code == 200
                data_turn2 = sync_resp.json()
                assert "6,0 metros" in data_turn2["response"]
                assert data_turn2["session_id"] == session_id_str

                # Telemetria do turno 2 foi acionada
                mock_persist_turn2.assert_awaited_once()

            # -------------------------------------------------------------
            # 5. Consulta dos Detalhes da Sessão (/api/v1/sessions/{id})
            # -------------------------------------------------------------
            get_session_resp = await async_client.get(
                f"/api/v1/sessions/{session_id_str}", headers=auth_headers
            )
            assert get_session_resp.status_code == 200
            session_detail = get_session_resp.json()
            assert session_detail["id"] == session_id_str
            assert len(session_detail["messages"]) >= 2

            # -------------------------------------------------------------
            # 6. Validação de TTL e Expiração (HTTP 410 Gone)
            # -------------------------------------------------------------
            # Simula inatividade superior ao TTL de 1 hora
            old_time = datetime.now(UTC) - timedelta(hours=2)
            expired_session = ChatSession(
                id=session_id,
                created_at=old_time - timedelta(minutes=10),
                updated_at=old_time,
            )
            mock_db_expired = MagicMock()
            mock_db_expired.scalar_one_or_none.return_value = expired_session
            mock_db.execute.side_effect = None
            mock_db.execute.return_value = mock_db_expired

            expired_payload = {
                "session_id": session_id_str,
                "message": "Mensagem após expiração",
                "stream": False,
            }
            expired_resp = await async_client.post(
                "/api/v1/chat", json=expired_payload, headers=auth_headers
            )
            assert expired_resp.status_code == 410
            assert "expirada" in expired_resp.json()["detail"].lower()

        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_db_session, None)
