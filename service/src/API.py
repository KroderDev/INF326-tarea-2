import datetime
import logging
import os
import uuid
from logging.handlers import RotatingFileHandler
from typing import Any, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

import Controller
from db.sqlc import models as sqlc_models
import cache as cache_recent

# Configuración de logs del servicio
DIR = os.path.normpath("/app/logs")
NAME = "logsAPI.log"
os.makedirs(DIR, exist_ok=True)
app = FastAPI(title="Messages Service API")


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    log_path = os.path.join(DIR, NAME)
    handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def set_info(msg: str) -> None:
    LOGS.info(msg)
    for h in LOGS.handlers:
        try:
            h.flush()
        except Exception:
            pass


LOGS = get_logger("API_logs")


# Modelos de entrada/salida
class MessageCreateIn(BaseModel):
    content: str = Field(..., description="Message content")
    type: Optional[sqlc_models.Type] = Field(None, description="Message type")
    paths: Optional[List[str]] = Field(None, description="Associated paths")


class MessageUpdateIn(BaseModel):
    content: Optional[str] = Field(None)
    paths: Optional[List[str]] = Field(None)


class MessageOut(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    user_id: uuid.UUID
    type: Optional[sqlc_models.Type] = None
    content: Optional[str] = None
    paths: Optional[List[str]] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None


async def get_user_id(x_user_id: str = Header(..., alias="X-User-Id")) -> uuid.UUID:
    """Get user_id from X-User-Id header."""
    try:
        return uuid.UUID(x_user_id)
    except Exception as e:  # 400 para header inválido
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def map_error_to_http(error: Exception) -> HTTPException:
    """Map controller exceptions to HTTP status codes."""
    msg = str(error)
    lower = msg.lower()
    if "no row returned" in lower or "not found" in lower:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)


def to_message_out(row: dict[str, Any]) -> MessageOut:
    """Convierte dict de DB a esquema público."""
    return MessageOut(**row)


@app.post(
    "/threads/{thread_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageOut,
    tags=["messages"],
)
async def create_message(
    thread_id: uuid.UUID,
    payload: MessageCreateIn,
    user_id: uuid.UUID = Depends(get_user_id),
):
    set_info(f"Create message thread={thread_id} user={user_id} type={payload.type}")
    resultado, error = await Controller.CreateMessage(
        thread_id, user_id, payload.content, payload.type, payload.paths
    )
    if error is not None:
        raise map_error_to_http(error)
    assert resultado is not None
    # Invalidar caché del hilo tras crear un mensaje
    await cache_recent.invalidate_thread(str(thread_id))
    return to_message_out(resultado)


@app.put(
    "/threads/{thread_id}/messages/{message_id}",
    response_model=MessageOut,
    tags=["messages"],
)
async def update_message(
    thread_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: MessageUpdateIn,
    user_id: uuid.UUID = Depends(get_user_id),
):
    set_info(f"Update message thread={thread_id} msg={message_id} user={user_id}")
    resultado, error = await Controller.UpdateMessage(
        thread_id, message_id, user_id, payload.content, None, payload.paths
    )
    if error is not None:
        raise map_error_to_http(error)
    assert resultado is not None
    # Invalidar caché tras actualizar
    await cache_recent.invalidate_thread(str(thread_id))
    return to_message_out(resultado)


@app.delete(
    "/threads/{thread_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["messages"],
)
async def delete_message(
    thread_id: uuid.UUID,
    message_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_user_id),
):
    set_info(f"Delete message thread={thread_id} msg={message_id} user={user_id}")
    resultado, error = await Controller.DeleteMessage(thread_id, message_id, user_id)
    if error is not None:
        raise map_error_to_http(error)
    # Invalidar caché tras eliminar
    await cache_recent.invalidate_thread(str(thread_id))
    return None


@app.get(
    "/threads/{thread_id}/messages",
    response_model=List[MessageOut],
    tags=["messages"],
)
async def list_messages(
    thread_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200, description="Number of messages"),
):
    set_info(f"List messages thread={thread_id} limit={limit}")
    # Cache-aside: intentar Redis para recientes si está dentro del tamaño máximo de caché
    recent: Optional[List[dict]] = None
    if limit <= cache_recent.CACHE_MAX_ITEMS:
        recent = await cache_recent.get_recent_messages(str(thread_id), limit)
    if recent is not None:
        # Log: retorno desde caché
        set_info(f"Cache hit thread={thread_id} items={len(recent)} limit={limit}")
        return [to_message_out(r) for r in recent]

    # Si no hay caché, consultar a la base de datos vía controlador
    resultado, error = await Controller.ListMessages(thread_id, 1, str(limit))
    if error is not None:
        raise map_error_to_http(error)
    assert resultado is not None

    # Poblar caché con hasta CACHE_MAX_ITEMS mensajes
    await cache_recent.set_recent_messages(str(thread_id), resultado)
    return [to_message_out(r) for r in resultado]
