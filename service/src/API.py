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
    content: str = Field(..., description="Contenido del mensaje")
    type: Optional[sqlc_models.Type] = Field(None, description="Tipo de mensaje")
    paths: Optional[List[str]] = Field(None, description="Rutas asociadas")


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
    """Obtiene el user_id desde el header X-User-Id."""
    try:
        return uuid.UUID(x_user_id)
    except Exception as e:  # 400 para header inválido
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def map_error_to_http(error: Exception) -> HTTPException:
    """Mapea errores del controlador a códigos HTTP."""
    msg = str(error)
    if "No se retornó fila" in msg or "no encontrado" in msg.lower():
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
    set_info(f"Crear mensaje hilo={thread_id} user={user_id} type={payload.type}")
    resultado, error = await Controller.CreateMessage(
        thread_id, user_id, payload.content, payload.type, payload.paths
    )
    if error is not None:
        raise map_error_to_http(error)
    assert resultado is not None
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
    set_info(f"Actualizar mensaje hilo={thread_id} msg={message_id} user={user_id}")
    resultado, error = await Controller.UpdateMessage(
        thread_id, message_id, user_id, payload.content, None, payload.paths
    )
    if error is not None:
        raise map_error_to_http(error)
    assert resultado is not None
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
    set_info(f"Eliminar mensaje hilo={thread_id} msg={message_id} user={user_id}")
    resultado, error = await Controller.DeleteMessage(thread_id, message_id, user_id)
    if error is not None:
        raise map_error_to_http(error)
    return None


@app.get(
    "/threads/{thread_id}/messages",
    response_model=List[MessageOut],
    tags=["messages"],
)
async def list_messages(
    thread_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200, description="Cantidad de mensajes"),
):
    set_info(f"Listar mensajes hilo={thread_id} limit={limit}")
    # Compatibilidad con Controller.GetMessage (typeM=1 => por cantidad)
    resultado, error = await Controller.GetMessage(thread_id, 1, str(limit))
    if error is not None:
        raise map_error_to_http(error)
    assert resultado is not None
    return [to_message_out(r) for r in resultado]
