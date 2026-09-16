"""Endpoints REST para criação e consulta de sessões conversacionais (v1)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.api.deps import api_key_and_rate_limit, get_db
from lumi.schemas.chat import SourceMetadata
from lumi.schemas.session import (
    ChatMessageResponse,
    SessionCreateResponse,
    SessionDetailResponse,
)
from lumi.services.session_service import (
    SessionExpiredError,
    SessionNotFoundError,
    SessionService,
)

# Injeção assíncrona de sessão do banco de dados compatível com FastAPI
get_db_session = get_db

router = APIRouter(tags=["Sessões v1"])


@router.post(
    "",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criação de nova sessão conversacional",
    description="Inicializa uma nova sessão de chat com identificador único UUID e timestamps UTC.",
)
@router.post(
    "/",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_session(
    _auth: Annotated[str, Depends(api_key_and_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionCreateResponse:
    """Cria uma nova sessão e persiste no banco de dados."""
    service = SessionService(session=db)
    chat_session = await service.create_session()
    return SessionCreateResponse(
        id=chat_session.id,
        created_at=chat_session.created_at,
    )


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Detalhamento e histórico de mensagens da sessão",
    description="Recupera o histórico cronológico da sessão validando a política de inatividade (TTL de 1 hora).",
    responses={
        status.HTTP_200_OK: {
            "model": SessionDetailResponse,
            "description": "Sessão recuperada com sucesso",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Sessão não encontrada",
        },
        status.HTTP_410_GONE: {
            "description": "Sessão expirada por inatividade",
        },
    },
)
async def get_session_detail(
    session_id: UUID,
    _auth: Annotated[str, Depends(api_key_and_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionDetailResponse:
    """Recupera detalhes e histórico completo de mensagens de uma sessão."""
    service = SessionService(session=db)
    try:
        chat_session = await service.get_session_or_raise(session_id, check_ttl=True)
        messages = await service.get_history(session_id, session=chat_session)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sessão {session_id} não encontrada.",
        ) from None
    except SessionExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Sessão expirada por inatividade.",
        ) from None

    formatted_messages: list[ChatMessageResponse] = []
    for msg in messages:
        raw_sources = msg.sources or []
        parsed_sources: list[SourceMetadata] = []
        for s in raw_sources:
            if isinstance(s, SourceMetadata):
                parsed_sources.append(s)
            elif isinstance(s, dict):
                try:
                    parsed_sources.append(SourceMetadata(**s))
                except Exception:
                    doc_code = str(s.get("document_code") or s.get("code") or "DESCONHECIDO")
                    rev = str(s.get("revision") or "")
                    sec = str(s.get("section") or s.get("title") or "Geral")
                    page = max(1, int(s.get("page") or s.get("page_number") or 1))
                    score = min(
                        1.0, max(0.0, float(s.get("relevance_score") or s.get("score") or 0.0))
                    )
                    snip = str(s.get("snippet") or s.get("content") or "")
                    parsed_sources.append(
                        SourceMetadata(
                            document_code=doc_code,
                            revision=rev,
                            section=sec,
                            page=page,
                            relevance_score=score,
                            snippet=snip,
                        )
                    )

        formatted_messages.append(
            ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,  # type: ignore[arg-type]
                content=msg.content,
                sources=parsed_sources,
                created_at=msg.created_at,
            )
        )

    return SessionDetailResponse(
        id=chat_session.id,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
        messages=formatted_messages,
    )
