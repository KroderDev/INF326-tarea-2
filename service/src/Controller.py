import asyncio
import datetime
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

from clients.rabbitmq import SendEvent
from db.sqlc import models as sqlc_models
from db.sqlc.messages import (CREATE_MESSAGE, GET_MESSAGE_BY_ID_FOR_UPDATE,
                              LIST_THREAD_MESSAGES_NOT_DELETED_DESC_BEFORE,
                              LIST_THREAD_MESSAGES_NOT_DELETED_DESC_FIRST,
                              SOFT_DELETE_MESSAGE,
                              UPDATE_MESSAGE_CONTENT_AND_PATHS)

CHUNK_DATE, CHUNK_CANT = 10, 50  # 10 días y 50 mensajes

from db.connection import get_pool, prepare


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


async def _send_event_async(
    event_type: str, data: Dict[str, Any]
) -> Optional[Exception]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: SendEvent(event_type, data))


async def CreateMessage(
    thread: uuid.UUID,
    user: uuid.UUID,
    content: Optional[str],
    typeM: Optional[sqlc_models.Type],
    path: Optional[List[str]],
) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
    resultado: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None

    params = {
        "p1": _as_uuid(thread),
        "p2": _as_uuid(user),
        "p3": (typeM.value if isinstance(typeM, sqlc_models.Type) else typeM),
        "p4": content,
        "p5": path,
        "p6": None,  # created_at -> NOW() por defecto
        "p7": None,  # updated_at -> NOW() por defecto
    }
    sql, values = prepare(CREATE_MESSAGE, params)

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, *values)
            if row is None:
                raise Exception("No row returned when creating message")
            resultado = dict(row)

        await _send_event_async(
            "CREATE",
            {
                "tag": "messages_service",
                "message": resultado,
            },
        )
    except Exception as e:
        error = e

    return resultado, error


async def UpdateMessage(
    thread: uuid.UUID,
    message: uuid.UUID,
    user: uuid.UUID,
    content: Optional[str],
    typeM: Optional[sqlc_models.Type],
    path: Optional[List[str]],
) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
    # Nota: solo usamos queries de sqlc
    resultado: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # 1) Validar pertenencia al thread (y bloquear fila para actualización)
            sel_sql, sel_vals = prepare(
                GET_MESSAGE_BY_ID_FOR_UPDATE, {"p1": _as_uuid(message)}
            )
            current = await conn.fetchrow(sel_sql, *sel_vals)
            if current is None or current.get("thread_id") != _as_uuid(thread):
                raise Exception("No row returned when updating message")

            # 2) Actualizar contenido/paths usando query de sqlc
            upd_sql, upd_vals = prepare(
                UPDATE_MESSAGE_CONTENT_AND_PATHS,
                {
                    "p1": _as_uuid(message),
                    "p2": content,
                    "p3": path,
                    "p4": None,  # updated_at -> NOW() por defecto
                },
            )
            row = await conn.fetchrow(upd_sql, *upd_vals)
            if row is None:
                raise Exception("No row returned when updating message")
            resultado = dict(row)
    except Exception as e:
        error = e

    return resultado, error


async def DeleteMessage(
    thread: uuid.UUID, message: uuid.UUID, user: uuid.UUID
) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
    # Borrado suave por defecto
    resultado: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # 1) Validar pertenencia al thread y que no esté borrado
            sel_sql, sel_vals = prepare(
                GET_MESSAGE_BY_ID_FOR_UPDATE, {"p1": _as_uuid(message)}
            )
            current = await conn.fetchrow(sel_sql, *sel_vals)
            if (
                current is None
                or current.get("thread_id") != _as_uuid(thread)
                or current.get("deleted_at") is not None
            ):
                raise Exception("No row returned when deleting message")

            # 2) Ejecutar soft delete de sqlc
            del_sql, del_vals = prepare(
                SOFT_DELETE_MESSAGE, {"p1": _as_uuid(message), "p2": None}
            )
            row = await conn.fetchrow(del_sql, *del_vals)
            if row is None:
                raise Exception("No row returned when deleting message")
            resultado = dict(row)
    except Exception as e:
        error = e

    return resultado, error


"""
Tipos de llamada para gestionar:
    - GET /message/{thread}                -> últimos mensajes no borrados (chunk por cantidad)
    - GET /message/{thread}?typeM=1&filtro={n} -> últimos n mensajes
    - GET /message/{thread}?typeM=-1&filtro={fecha} -> por fecha (pendiente)
"""


async def ListMessages(
    thread: uuid.UUID,
    typeM: Optional[int],
    filtro: Optional[str],
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Exception]]:
    # Si typeM == 1 -> filtro por cantidad (n últimos)
    # Si typeM == -1 -> filtro por fecha (PENDIENTE)
    resultado: Optional[List[Dict[str, Any]]] = None
    error: Optional[Exception] = None

    limit = CHUNK_CANT
    if typeM == 1 and filtro is not None:
        try:
            limit = max(1, int(filtro))
        except ValueError:
            pass

    params = {"p1": _as_uuid(thread), "p2": limit}
    sql, values = prepare(LIST_THREAD_MESSAGES_NOT_DELETED_DESC_FIRST, params)

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *values)
            resultado = [dict(r) for r in rows]
    except Exception as e:
        error = e

    return resultado, error


async def ListMessagesBefore(
    thread: uuid.UUID,
    created_at: datetime.datetime,
    message_id: uuid.UUID,
    limit: int,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Exception]]:
    resultado: Optional[List[Dict[str, Any]]] = None
    error: Optional[Exception] = None

    params = {
        "p1": _as_uuid(thread),
        "p2": created_at,
        "p3": _as_uuid(message_id),
        "p4": limit,
    }
    sql, values = prepare(LIST_THREAD_MESSAGES_NOT_DELETED_DESC_BEFORE, params)

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *values)
            resultado = [dict(r) for r in rows]
    except Exception as e:
        error = e

    return resultado, error
