"""Testes unitários para os schemas Pydantic de Chat, Sessão e Eventos SSE."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from lumi.schemas import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    SessionCreateResponse,
    SessionDetailResponse,
    SourceMetadata,
    StreamDoneEvent,
    StreamErrorEvent,
    StreamSourcesEvent,
    StreamTokenEvent,
)


class TestSourceMetadata:
    """Testes para o schema SourceMetadata."""

    def test_source_metadata_valid(self) -> None:
        source = SourceMetadata(
            document_code="DIS-NOR-030",
            revision="REV07",
            section="Item 5.3 — Dimensionamento",
            page=28,
            relevance_score=0.89,
            snippet="Para edifícios residenciais com até 24 unidades...",
        )
        assert source.document_code == "DIS-NOR-030"
        assert source.revision == "REV07"
        assert source.section == "Item 5.3 — Dimensionamento"
        assert source.page == 28
        assert source.relevance_score == 0.89
        assert source.snippet == "Para edifícios residenciais com até 24 unidades..."

    def test_source_metadata_score_boundaries(self) -> None:
        s_min = SourceMetadata(
            document_code="DIS-NOR-030",
            revision="REV01",
            section="Seção 1",
            page=1,
            relevance_score=0.0,
            snippet="Início",
        )
        assert s_min.relevance_score == 0.0

        s_max = SourceMetadata(
            document_code="DIS-NOR-030",
            revision="REV01",
            section="Seção 1",
            page=1,
            relevance_score=1.0,
            snippet="Fim",
        )
        assert s_max.relevance_score == 1.0

    def test_source_metadata_defaults(self) -> None:
        source = SourceMetadata(
            document_code="DIS-NOR-030",
            section="Item 2.1",
            page=5,
            relevance_score=0.75,
        )
        assert source.revision == ""
        assert source.snippet == ""

    @pytest.mark.parametrize("invalid_page", [0, -1, -99])
    def test_source_metadata_invalid_page(self, invalid_page: int) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SourceMetadata(
                document_code="DIS-NOR-030",
                section="Item 1",
                page=invalid_page,
                relevance_score=0.5,
            )
        assert "page" in str(exc_info.value)

    @pytest.mark.parametrize("invalid_score", [-0.01, 1.01, -1.0, 2.5])
    def test_source_metadata_invalid_relevance_score(self, invalid_score: float) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SourceMetadata(
                document_code="DIS-NOR-030",
                section="Item 1",
                page=1,
                relevance_score=invalid_score,
            )
        assert "relevance_score" in str(exc_info.value)

    def test_source_metadata_empty_document_code(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SourceMetadata(
                document_code="",
                section="Item 1",
                page=1,
                relevance_score=0.5,
            )
        assert "document_code" in str(exc_info.value)


class TestChatRequest:
    """Testes para o schema ChatRequest."""

    def test_chat_request_valid_with_default_stream(self) -> None:
        sess_id = uuid4()
        req = ChatRequest(
            session_id=sess_id,
            message="Como dimensionar entrada coletiva?",
        )
        assert req.session_id == sess_id
        assert req.message == "Como dimensionar entrada coletiva?"
        assert req.stream is True

    def test_chat_request_explicit_stream_false(self) -> None:
        sess_id = uuid4()
        req = ChatRequest(
            session_id=sess_id,
            message="Pergunta síncrona",
            stream=False,
        )
        assert req.stream is False

    def test_chat_request_accepts_uuid_string(self) -> None:
        sess_uuid = uuid4()
        req = ChatRequest(
            session_id=str(sess_uuid),
            message="Pergunta com UUID em string",
        )
        assert req.session_id == sess_uuid
        assert isinstance(req.session_id, UUID)

    def test_chat_request_invalid_uuid(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                session_id="uuid-invalido-1234",
                message="Pergunta qualquer",
            )
        assert "session_id" in str(exc_info.value)

    @pytest.mark.parametrize("invalid_message", ["", "   ", " \t \n  "])
    def test_chat_request_rejects_empty_or_whitespace_message(self, invalid_message: str) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                session_id=uuid4(),
                message=invalid_message,
            )
        assert "message" in str(exc_info.value)


class TestChatResponse:
    """Testes para o schema ChatResponse."""

    def test_chat_response_valid_defaults(self) -> None:
        sess_id = uuid4()
        resp = ChatResponse(
            session_id=sess_id,
            response="Resposta técnica do assistente.",
        )
        assert resp.session_id == sess_id
        assert resp.response == "Resposta técnica do assistente."
        assert resp.sources == []
        assert isinstance(resp.created_at, datetime)

    def test_chat_response_with_sources_and_datetime(self) -> None:
        sess_id = uuid4()
        source = SourceMetadata(
            document_code="DIS-NOR-030",
            revision="REV07",
            section="Tabela 4",
            page=30,
            relevance_score=0.92,
            snippet="Trecho de referência",
        )
        now = datetime.now(UTC)
        resp = ChatResponse(
            session_id=sess_id,
            response="Resposta técnica.",
            sources=[source],
            created_at=now,
        )
        assert resp.session_id == sess_id
        assert len(resp.sources) == 1
        assert resp.sources[0].document_code == "DIS-NOR-030"
        assert resp.created_at == now


class TestStreamEvents:
    """Testes para os schemas de eventos SSE."""

    def test_stream_token_event(self) -> None:
        event = StreamTokenEvent(token="Olá, ")
        assert event.token == "Olá, "

    def test_stream_token_event_empty_token_allowed(self) -> None:
        event = StreamTokenEvent(token="")
        assert event.token == ""

    def test_stream_sources_event(self) -> None:
        source = SourceMetadata(
            document_code="DIS-NOR-030",
            section="Item 5.3",
            page=28,
            relevance_score=0.85,
        )
        event = StreamSourcesEvent(sources=[source])
        assert len(event.sources) == 1
        assert event.sources[0].page == 28

    def test_stream_sources_event_default_empty_list(self) -> None:
        event = StreamSourcesEvent()
        assert event.sources == []

    def test_stream_done_event(self) -> None:
        sess_id = uuid4()
        event = StreamDoneEvent(session_id=sess_id)
        assert event.session_id == sess_id

    def test_stream_done_event_invalid_uuid(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            StreamDoneEvent(session_id="invalido")
        assert "session_id" in str(exc_info.value)

    def test_stream_error_event(self) -> None:
        event = StreamErrorEvent(
            error="Erro ao conectar com provedor de LLM.",
            code="LLM_STREAM_ERROR",
        )
        assert event.error == "Erro ao conectar com provedor de LLM."
        assert event.code == "LLM_STREAM_ERROR"

    def test_stream_error_event_validation(self) -> None:
        with pytest.raises(ValidationError):
            StreamErrorEvent.model_validate({"error": "Erro sem code"})


class TestSessionSchemas:
    """Testes para os schemas de Sessão e Histórico."""

    def test_session_create_response(self) -> None:
        sess_id = uuid4()
        resp = SessionCreateResponse(id=sess_id)
        assert resp.id == sess_id
        assert resp.session_id == sess_id
        assert isinstance(resp.created_at, datetime)

    def test_session_create_response_alias_support(self) -> None:
        sess_id = uuid4()
        resp = SessionCreateResponse(session_id=sess_id)
        assert resp.id == sess_id
        assert resp.session_id == sess_id

    @pytest.mark.parametrize("role", ["user", "assistant", "system"])
    def test_chat_message_response_valid_roles(self, role: str) -> None:
        sess_id = uuid4()
        msg = ChatMessageResponse(
            session_id=sess_id,
            role=role,
            content="Mensagem de teste",
        )
        assert msg.session_id == sess_id
        assert msg.role == role
        assert msg.content == "Mensagem de teste"
        assert msg.sources == []
        assert isinstance(msg.id, UUID)
        assert isinstance(msg.created_at, datetime)

    @pytest.mark.parametrize("invalid_role", ["admin", "bot", "guest", "moderator", ""])
    def test_chat_message_response_invalid_role(self, invalid_role: str) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ChatMessageResponse(
                session_id=uuid4(),
                role=invalid_role,
                content="Mensagem com papel inválido",
            )
        assert "role" in str(exc_info.value)

    def test_session_detail_response(self) -> None:
        sess_id = uuid4()
        msg1 = ChatMessageResponse(
            session_id=sess_id,
            role="user",
            content="Qual a demanda?",
        )
        msg2 = ChatMessageResponse(
            session_id=sess_id,
            role="assistant",
            content="A demanda é...",
            sources=[
                SourceMetadata(
                    document_code="DIS-NOR-030",
                    section="5.1",
                    page=10,
                    relevance_score=0.9,
                )
            ],
        )
        detail = SessionDetailResponse(
            id=sess_id,
            messages=[msg1, msg2],
        )
        assert detail.id == sess_id
        assert detail.session_id == sess_id
        assert len(detail.messages) == 2
        assert detail.messages[0].role == "user"
        assert detail.messages[1].role == "assistant"
        assert len(detail.messages[1].sources) == 1
        assert isinstance(detail.created_at, datetime)
        assert isinstance(detail.updated_at, datetime)

    def test_session_detail_response_alias_support(self) -> None:
        sess_id = uuid4()
        detail = SessionDetailResponse(session_id=sess_id)
        assert detail.id == sess_id
        assert detail.session_id == sess_id
        assert detail.messages == []
