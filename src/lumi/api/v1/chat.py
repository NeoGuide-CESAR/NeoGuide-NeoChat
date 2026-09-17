"""Endpoints REST e streaming Server-Sent Events (SSE) para conversação (v1)."""

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from lumi.api.deps import api_key_and_rate_limit, get_db
from lumi.schemas.chat import ChatRequest
from lumi.services.chat_service import ChatService
from lumi.services.session_service import (
    SessionExpiredError,
    SessionNotFoundError,
    SessionService,
)

# Injeção assíncrona de sessão do banco de dados compatível com FastAPI
get_db_session = get_db

router = APIRouter(tags=["Chat v1"])


@router.post(
    "",
    summary="Interação conversacional com a Lumi (SSE ou síncrono)",
    description=(
        "Endpoint principal para envio de mensagens com suporte à transmissão progressiva de "
        "tokens via Server-Sent Events (SSE) ou retorno síncrono consolidado (ChatResponse)."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "Resposta síncrona JSON ou fluxo streaming text/event-stream.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Chave de API ausente ou inválida.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Sessão não encontrada no banco de dados.",
        },
        status.HTTP_410_GONE: {
            "description": "Sessão expirada por inatividade (TTL de 1 hora).",
        },
    },
)
@router.post(
    "/",
    include_in_schema=False,
)
async def chat_endpoint(
    request: ChatRequest,
    _auth: Annotated[str, Depends(api_key_and_rate_limit)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
) -> Any:
    """Processa a mensagem do usuário via streaming SSE ou resposta síncrona."""
    session_service = SessionService(session=db)

    # Validação antecipada de sessão para garantia de códigos HTTP 404 e 410 antes dos headers SSE
    try:
        await session_service.get_session_or_raise(request.session_id, check_ttl=True)
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sessão {request.session_id} não encontrada.",
        ) from None
    except SessionExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Sessão expirada por inatividade.",
        ) from None

    chat_service = ChatService(session=db, session_service=session_service)

    if request.stream:
        return StreamingResponse(
            chat_service.stream_chat(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await chat_service.process_chat(request, background_tasks=background_tasks)
