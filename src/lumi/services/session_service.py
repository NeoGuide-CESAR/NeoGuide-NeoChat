"""Serviço de gerenciamento do ciclo de vida de sessões conversacionais e histórico."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.core.config import Settings, get_settings
from lumi.db.models import ChatMessage, ChatSession


class SessionError(Exception):
    """Exceção base para operações de sessão conversacional."""


class SessionNotFoundError(SessionError):
    """Exceção lançada quando a sessão informada não for localizada."""


class SessionExpiredError(SessionError):
    """Exceção lançada quando a sessão informada expirou por inatividade."""


class SessionService:
    """Gerencia o ciclo de vida, persistência e janela de histórico de sessões de chat."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    async def create_session(self, session_id: UUID | None = None) -> ChatSession:
        """Cria uma nova sessão conversacional no banco de dados.

        Args:
            session_id: Identificador opcional da sessão (gera UUIDv4 se None).

        Returns:
            ChatSession instanciada e persistida.
        """
        sid = session_id or uuid4()
        now = datetime.now(UTC)
        chat_session = ChatSession(
            id=sid,
            created_at=now,
            updated_at=now,
        )
        self.session.add(chat_session)
        await self.session.flush()
        return chat_session

    async def get_session(self, session_id: UUID, check_ttl: bool = True) -> ChatSession | None:
        """Recupera uma sessão pelo identificador, opcionalmente validando TTL de inatividade.

        Args:
            session_id: Identificador UUID da sessão.
            check_ttl: Se True, valida se a sessão ultrapassou o tempo limite de inatividade.

        Raises:
            SessionExpiredError: Se check_ttl for True e o tempo de inatividade exceder o TTL.

        Returns:
            ChatSession se encontrada, ou None se inexistente.
        """
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()

        if chat_session is None:
            return None

        if check_ttl:
            now = datetime.now(UTC)
            updated_at = chat_session.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)

            elapsed_seconds = (now - updated_at).total_seconds()
            ttl_seconds = self.settings.session_ttl_hours * 3600

            if elapsed_seconds > ttl_seconds:
                raise SessionExpiredError(f"Sessão {session_id} expirada por inatividade.")

        return chat_session

    async def get_session_or_raise(self, session_id: UUID, check_ttl: bool = True) -> ChatSession:
        """Recupera uma sessão ou levanta SessionNotFoundError se inexistente.

        Args:
            session_id: Identificador UUID da sessão.
            check_ttl: Se True, valida expiração por TTL de inatividade.

        Raises:
            SessionNotFoundError: Se a sessão não existir.
            SessionExpiredError: Se a sessão estiver expirada.

        Returns:
            ChatSession localizada.
        """
        chat_session = await self.get_session(session_id, check_ttl=check_ttl)
        if chat_session is None:
            raise SessionNotFoundError(f"Sessão {session_id} não encontrada.")
        return chat_session

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> ChatMessage:
        """Adiciona uma nova mensagem à sessão e renova seu timestamp de atividade (updated_at).

        Args:
            session_id: Identificador UUID da sessão vinculada.
            role: Papel do emissor ('user', 'assistant', 'system').
            content: Conteúdo textual da mensagem.
            sources: Metadados opcionais de fontes normativas anexadas.

        Raises:
            SessionNotFoundError: Se a sessão não existir.
            SessionExpiredError: Se a sessão estiver expirada.

        Returns:
            ChatMessage instanciada e persistida.
        """
        chat_session = await self.get_session_or_raise(session_id, check_ttl=True)

        now = datetime.now(UTC)
        chat_session.updated_at = now

        msg = ChatMessage(
            id=uuid4(),
            session_id=session_id,
            role=role,
            content=content,
            sources=sources or [],
            created_at=now,
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_history(
        self,
        session_id: UUID,
        limit: int | None = None,
        session: ChatSession | None = None,
    ) -> list[ChatMessage]:
        """Consulta o histórico de mensagens da sessão em ordem cronológica ascendente (ASC).

        Args:
            session_id: Identificador UUID da sessão.
            limit: Limite máximo das mensagens mais recentes a recuperar.
            session: Instância de ChatSession previamente validada (opcional).

        Raises:
            SessionNotFoundError: Se a sessão não existir.
            SessionExpiredError: Se a sessão estiver expirada.

        Returns:
            Lista de ChatMessage ordenada por created_at ASC.
        """
        if session is None:
            await self.get_session_or_raise(session_id, check_ttl=True)

        if limit is not None:
            if limit <= 0:
                return []
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            messages = list(result.scalars().all())
            messages.reverse()
            return messages

        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_langchain_messages(
        self, session_id: UUID, limit: int | None = None
    ) -> list[BaseMessage]:
        """Recupera mensagens do histórico e as converte para instâncias do LangChain.

        Args:
            session_id: Identificador UUID da sessão.
            limit: Limite máximo de mensagens recentes.

        Raises:
            SessionNotFoundError: Se a sessão não existir.
            SessionExpiredError: Se a sessão estiver expirada.

        Returns:
            Lista de BaseMessage (HumanMessage, AIMessage, SystemMessage) em ordem cronológica.
        """
        messages = await self.get_history(session_id, limit=limit)
        langchain_msgs: list[BaseMessage] = []

        for msg in messages:
            if msg.role == "user":
                langchain_msgs.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_msgs.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                langchain_msgs.append(SystemMessage(content=msg.content))
            else:
                langchain_msgs.append(HumanMessage(content=msg.content))

        return langchain_msgs
