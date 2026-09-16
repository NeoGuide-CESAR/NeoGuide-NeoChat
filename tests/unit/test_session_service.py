"""Testes unitários para o serviço SessionService e ciclo de vida de sessões e mensagens."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.core.config import Settings
from lumi.db.models import ChatMessage, ChatSession
from lumi.services.session_service import (
    SessionError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionService,
)


@pytest.fixture
def mock_db() -> AsyncMock:
    """Fixture de sessão SQLAlchemy assíncrona mockada."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    return db


@pytest.fixture
def test_settings() -> Settings:
    """Configuração de teste com TTL de 1 hora e limite de histórico 10."""
    return Settings(session_ttl_hours=1, chat_history_limit=10)


@pytest.fixture
def session_service(mock_db: AsyncMock, test_settings: Settings) -> SessionService:
    """Instância de SessionService sob teste."""
    return SessionService(session=mock_db, settings=test_settings)


class TestSessionServiceCreation:
    """Testes de criação de sessões conversacionais."""

    @pytest.mark.asyncio
    async def test_create_session_generates_unique_id(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida que create_session sem ID prévio gera um novo UUID único e persiste."""
        session1 = await session_service.create_session()
        session2 = await session_service.create_session()

        assert isinstance(session1, ChatSession)
        assert isinstance(session2, ChatSession)
        assert session1.id != session2.id
        assert session1.created_at is not None
        assert session1.updated_at is not None
        assert mock_db.add.call_count == 2
        assert mock_db.flush.await_count == 2

    @pytest.mark.asyncio
    async def test_create_session_with_explicit_id(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida que create_session respeita um session_id informado explicitamente."""
        custom_id = uuid4()
        session = await session_service.create_session(session_id=custom_id)

        assert session.id == custom_id
        mock_db.add.assert_called_once_with(session)
        mock_db.flush.assert_awaited_once()


class TestSessionServiceRetrieval:
    """Testes de recuperação de sessões e tratamento de exceções."""

    @pytest.mark.asyncio
    async def test_get_session_found(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida recuperação bem-sucedida de sessão existente e ativa."""
        session_id = uuid4()
        existing_session = ChatSession(
            id=session_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_session
        mock_db.execute.return_value = mock_result

        retrieved = await session_service.get_session(session_id)
        assert retrieved is existing_session
        assert retrieved.id == session_id

    @pytest.mark.asyncio
    async def test_get_session_not_found_returns_none(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida que get_session retorna None quando a sessão não existe."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await session_service.get_session(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_or_raise_success(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida que get_session_or_raise retorna a sessão quando existente."""
        session_id = uuid4()
        existing_session = ChatSession(
            id=session_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_session
        mock_db.execute.return_value = mock_result

        retrieved = await session_service.get_session_or_raise(session_id)
        assert retrieved is existing_session

    @pytest.mark.asyncio
    async def test_get_session_or_raise_not_found(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida que get_session_or_raise levanta SessionNotFoundError quando não encontrada."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        target_id = uuid4()
        with pytest.raises(SessionNotFoundError) as exc_info:
            await session_service.get_session_or_raise(target_id)

        assert str(target_id) in str(exc_info.value)
        assert issubclass(SessionNotFoundError, SessionError)


class TestSessionServiceTtlExpiration:
    """Testes de política de expiração por inatividade (TTL de 1h - RN-05)."""

    @pytest.mark.asyncio
    async def test_get_session_expired_raises_session_expired_error(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida que sessão inativa há mais de 1 hora levanta SessionExpiredError com check_ttl=True."""
        session_id = uuid4()
        expired_time = datetime.now(UTC) - timedelta(hours=1, minutes=5)
        expired_session = ChatSession(
            id=session_id,
            created_at=expired_time - timedelta(hours=1),
            updated_at=expired_time,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expired_session
        mock_db.execute.return_value = mock_result

        with pytest.raises(SessionExpiredError) as exc_info:
            await session_service.get_session(session_id, check_ttl=True)

        assert str(session_id) in str(exc_info.value)
        assert "expirada" in str(exc_info.value).lower()
        assert issubclass(SessionExpiredError, SessionError)

    @pytest.mark.asyncio
    async def test_get_session_expired_ignored_when_check_ttl_false(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida que verificação de TTL pode ser ignorada com check_ttl=False."""
        session_id = uuid4()
        expired_time = datetime.now(UTC) - timedelta(hours=2)
        expired_session = ChatSession(
            id=session_id,
            created_at=expired_time - timedelta(hours=1),
            updated_at=expired_time,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expired_session
        mock_db.execute.return_value = mock_result

        retrieved = await session_service.get_session(session_id, check_ttl=False)
        assert retrieved is expired_session

    @pytest.mark.asyncio
    async def test_get_session_handles_naive_and_aware_datetime(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Garante tratamento robusto de timezone sem levantar erro de compatibilidade de datetime."""
        session_id = uuid4()
        # Datetime naive (sem fuso horário explícito) simulando retorno de alguns drivers
        naive_recent = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=10)
        session = ChatSession(
            id=session_id,
            created_at=naive_recent,
            updated_at=naive_recent,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = session
        mock_db.execute.return_value = mock_result

        retrieved = await session_service.get_session(session_id, check_ttl=True)
        assert retrieved is session


class TestSessionServiceMessagesAndHistory:
    """Testes de inserção de mensagens e recuperação de histórico ordenado."""

    @pytest.mark.asyncio
    async def test_add_message_updates_session_timestamp(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida que add_message cria mensagem e atualiza updated_at da sessão."""
        session_id = uuid4()
        old_time = datetime.now(UTC) - timedelta(minutes=30)
        session = ChatSession(
            id=session_id,
            created_at=old_time,
            updated_at=old_time,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = session
        mock_db.execute.return_value = mock_result

        sources = [{"code": "DIS-NOR-030", "title": "Critérios de Redes", "score": 0.95}]
        msg = await session_service.add_message(
            session_id=session_id,
            role="user",
            content="Qual a altura mínima de poste?",
            sources=sources,
        )

        assert isinstance(msg, ChatMessage)
        assert msg.session_id == session_id
        assert msg.role == "user"
        assert msg.content == "Qual a altura mínima de poste?"
        assert msg.sources == sources
        # updated_at da sessão deve ter sido renovado para o instante atual
        assert session.updated_at > old_time
        mock_db.add.assert_called_once_with(msg)
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_message_raises_on_expired_session(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida que add_message em sessão inativa há mais de 1h levanta SessionExpiredError."""
        session_id = uuid4()
        expired_time = datetime.now(UTC) - timedelta(hours=2)
        expired_session = ChatSession(
            id=session_id,
            created_at=expired_time,
            updated_at=expired_time,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expired_session
        mock_db.execute.return_value = mock_result

        with pytest.raises(SessionExpiredError):
            await session_service.add_message(
                session_id=session_id,
                role="user",
                content="Tentativa em sessão expirada",
            )

    @pytest.mark.asyncio
    async def test_get_history_ordered_asc_with_limit(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida que get_history recupera as mensagens ordenadas cronologicamente (ASC)."""
        session_id = uuid4()
        active_session = ChatSession(
            id=session_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Mock da busca da sessão
        mock_session_res = MagicMock()
        mock_session_res.scalar_one_or_none.return_value = active_session

        # Mock das mensagens (retornadas em DESC na consulta com limite, mas devem ser invertidas para ASC)
        t0 = datetime.now(UTC) - timedelta(minutes=5)
        t1 = datetime.now(UTC) - timedelta(minutes=3)
        t2 = datetime.now(UTC) - timedelta(minutes=1)
        m1 = ChatMessage(session_id=session_id, role="user", content="M1", created_at=t0)
        m2 = ChatMessage(session_id=session_id, role="assistant", content="M2", created_at=t1)
        m3 = ChatMessage(session_id=session_id, role="user", content="M3", created_at=t2)

        # Simulando query com order_by(created_at.desc()) onde DB retorna [m3, m2, m1]
        mock_msgs_res = MagicMock()
        mock_msgs_res.scalars.return_value.all.return_value = [m3, m2, m1]

        mock_db.execute.side_effect = [mock_session_res, mock_msgs_res]

        history = await session_service.get_history(session_id=session_id, limit=3)

        # O retorno deve estar em ordem estritamente ASC [m1, m2, m3]
        assert len(history) == 3
        assert history[0].content == "M1"
        assert history[1].content == "M2"
        assert history[2].content == "M3"

    @pytest.mark.asyncio
    async def test_get_langchain_messages_conversion(
        self, session_service: SessionService, mock_db: AsyncMock
    ) -> None:
        """Valida a conversão do histórico em instâncias de mensagens LangChain."""
        session_id = uuid4()
        active_session = ChatSession(
            id=session_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_session_res = MagicMock()
        mock_session_res.scalar_one_or_none.return_value = active_session

        t0 = datetime.now(UTC) - timedelta(minutes=10)
        t1 = datetime.now(UTC) - timedelta(minutes=8)
        t2 = datetime.now(UTC) - timedelta(minutes=6)
        t3 = datetime.now(UTC) - timedelta(minutes=4)

        m_sys = ChatMessage(session_id=session_id, role="system", content="Contexto", created_at=t0)
        m_user = ChatMessage(session_id=session_id, role="user", content="Pergunta", created_at=t1)
        m_ai = ChatMessage(
            session_id=session_id, role="assistant", content="Resposta", created_at=t2
        )
        m_user2 = ChatMessage(
            session_id=session_id, role="user", content="Outra pergunta", created_at=t3
        )

        mock_msgs_res = MagicMock()
        mock_msgs_res.scalars.return_value.all.return_value = [m_sys, m_user, m_ai, m_user2]

        mock_db.execute.side_effect = [mock_session_res, mock_msgs_res]

        lc_messages = await session_service.get_langchain_messages(session_id=session_id)

        assert len(lc_messages) == 4
        assert isinstance(lc_messages[0], SystemMessage)
        assert lc_messages[0].content == "Contexto"

        assert isinstance(lc_messages[1], HumanMessage)
        assert lc_messages[1].content == "Pergunta"

        assert isinstance(lc_messages[2], AIMessage)
        assert lc_messages[2].content == "Resposta"

        assert isinstance(lc_messages[3], HumanMessage)
        assert lc_messages[3].content == "Outra pergunta"
