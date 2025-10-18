import datetime
import logging
import os
import uuid
from logging.handlers import RotatingFileHandler
from typing import Any, List, Optional, Tuple

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

import cache as cache_recent
import Controller
from db.sqlc import models as sqlc_models

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


class MessagesPageOut(BaseModel):
    items: List[MessageOut]
    next_cursor: Optional[str] = None
    has_more: bool = False


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
    resultado, error = await Controller.CreateMessage(
        thread_id, user_id, payload.content, payload.type, payload.paths
    )
    if error is not None:
        raise map_error_to_http(error)
    assert resultado is not None
    set_info(f"Create message thread={thread_id} user={user_id} type={payload.type}")
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
    resultado, error = await Controller.UpdateMessage(
        thread_id, message_id, user_id, payload.content, None, payload.paths
    )
    if error is not None:
        raise map_error_to_http(error)
    assert resultado is not None
    set_info(f"Update message thread={thread_id} msg={message_id} user={user_id}")
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
    resultado, error = await Controller.DeleteMessage(thread_id, message_id, user_id)
    if error is not None:
        raise map_error_to_http(error)
    set_info(f"Delete message thread={thread_id} msg={message_id} user={user_id}")
    # Invalidar caché tras eliminar
    await cache_recent.invalidate_thread(str(thread_id))
    return None


@app.get(
    "/threads/{thread_id}/messages",
    response_model=MessagesPageOut,
    tags=["messages"],
)
async def list_messages(
    thread_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200, description="Number of messages"),
    cursor: Optional[str] = Query(None, description="Cursor for keyset pagination"),
):
    set_info(
        f"List messages thread={thread_id} limit={limit} cursor={'set' if cursor else 'none'}"
    )

    def _parse_cursor(cur: str) -> Optional[Tuple[datetime.datetime, uuid.UUID]]:
        try:
            p = cur.split("|", 1)
            if len(p) != 2:
                return None
            ts = datetime.datetime.fromisoformat(p[0])
            mid = uuid.UUID(p[1])
            return ts, mid
        except Exception:
            return None

    def _make_cursor(item: dict[str, Any]) -> Optional[str]:
        ts = item.get("created_at")
        mid = item.get("id")
        if ts is None or mid is None:
            return None
        if isinstance(ts, datetime.datetime):
            ts_str = ts.isoformat()
        else:
            ts_str = str(ts)
        return f"{ts_str}|{mid}"

    if cursor is None and limit <= cache_recent.CACHE_MAX_ITEMS:
        recent = await cache_recent.get_recent_messages(str(thread_id), limit)
        if recent is not None:
            set_info(f"Cache hit thread={thread_id} items={len(recent)} limit={limit}")
            items = [to_message_out(r) for r in recent]
            next_cur = _make_cursor(recent[-1]) if len(recent) > 0 else None
            has_more = len(recent) == limit
            return MessagesPageOut(items=items, next_cursor=next_cur, has_more=has_more)

    before = _parse_cursor(cursor) if cursor else None
    if before is None and cursor is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor"
        )

    if before is None:
        resultado, error = await Controller.ListMessages(thread_id, 1, str(limit))
    else:
        ts, mid = before
        resultado, error = await Controller.ListMessagesBefore(
            thread_id, ts, mid, limit
        )
    if error is not None:
        raise map_error_to_http(error)
    assert resultado is not None

    if before is None:
        await cache_recent.set_recent_messages(str(thread_id), resultado)

    items = [to_message_out(r) for r in resultado]
    next_cur = _make_cursor(resultado[-1]) if len(resultado) > 0 else None
    has_more = len(resultado) == limit
    return MessagesPageOut(items=items, next_cursor=next_cur, has_more=has_more)
