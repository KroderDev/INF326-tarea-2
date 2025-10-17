import dataclasses
import datetime
import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

import pika
import sqlalchemy
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine

from db.sqlc import models as sqlc_models
from db.sqlc.messages import (CREATE_MESSAGE,
                              LIST_THREAD_MESSAGES_NOT_DELETED_DESC_FIRST,
                              SOFT_DELETE_MESSAGE,
                              UPDATE_MESSAGE_CONTENT_AND_PATHS)

CHUNK_DATE, CHUNK_CANT = 10, 50  # 10 días y 50 mensajes

QUEUE = {
    "user": os.getenv("QUEUE_USER", "root"),
    "password": os.getenv("QUEUE_PASSWORD", "secret"),
    "host": os.getenv("QUEUE_HOST", "localhost"),
    "port": int(os.getenv("QUEUE_PORT", "8002")),
}

DB = {
    "name": os.getenv("DB_NAME", "messages_service"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "secret"),
    "host": os.getenv("DB_HOST", "database"),
    "port": int(os.getenv("DB_PORT", "5432")),
}


def _db_url() -> str:
    return (
        f"postgresql+psycopg://{DB['user']}:{DB['password']}@"
        f"{DB['host']}:{DB['port']}/{DB['name']}"
    )


def get_engine() -> Engine:
    return create_engine(_db_url(), pool_size=5, max_overflow=5, future=True)


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def SendEvent(event_type: str, data: Dict[str, Any]) -> Optional[Exception]:
    error: Optional[Exception] = None
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=QUEUE["host"],
            port=QUEUE["port"],
            credentials=pika.PlainCredentials(QUEUE["user"], QUEUE["password"]),
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=data["tag"], durable=True)

    try:
        if event_type == "CREATE":
            message = data["message"]
            body = json.dumps(message, default=str)
            channel.basic_publish(
                exchange="",
                routing_key=data["tag"],
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
        else:
            error = Exception("Tipo de evento no soportado")
    except Exception as e:  # pragma: no cover (errores de red)
        error = e
    finally:
        connection.close()
    return error


def CreateMessage(
    thread: uuid.UUID,
    user: uuid.UUID,
    content: Optional[str],
    typeM: Optional[sqlc_models.Type],
    path: Optional[List[str]],
) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
    resultado: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None

    engine = get_engine()
    stmt = text(CREATE_MESSAGE).bindparams(
        bindparam("p5", type_=sqlalchemy.JSON)
    )  # paths JSONB
    params = {
        "p1": _as_uuid(thread),
        "p2": _as_uuid(user),
        "p3": (typeM.value if isinstance(typeM, sqlc_models.Type) else typeM),
        "p4": content,
        "p5": path,
        "p6": None,  # created_at -> NOW() por defecto
        "p7": None,  # updated_at -> NOW() por defecto
    }

    try:
        with engine.begin() as conn:
            res = conn.execute(stmt, params)
            row = res.mappings().one()
            resultado = dict(row)

        # Enviar evento después del éxito
        SendEvent(
            "CREATE",
            {
                "tag": "messages_service",
                "message": resultado,
            },
        )
    except Exception as e:
        error = e

    return resultado, error


def UpdateMessage(
    thread: uuid.UUID,
    message: uuid.UUID,
    user: uuid.UUID,
    content: Optional[str],
    typeM: Optional[sqlc_models.Type],  # no se actualiza con esta query
    path: Optional[List[str]],
) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
    # Nota: el SQL generado por sqlc solo actualiza content/paths
    resultado: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None

    engine = get_engine()
    stmt = text(UPDATE_MESSAGE_CONTENT_AND_PATHS).bindparams(
        bindparam("p3", type_=sqlalchemy.JSON)
    )
    params = {
        "p1": _as_uuid(message),
        "p2": content,
        "p3": path,
        "p4": None,  # updated_at -> NOW() por defecto
    }

    try:
        with engine.begin() as conn:
            res = conn.execute(stmt, params)
            row = res.mappings().one()
            resultado = dict(row)
    except Exception as e:
        error = e

    return resultado, error


def DeleteMessage(
    message: uuid.UUID, user: uuid.UUID
) -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
    # Borrado suave por defecto
    resultado: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None

    engine = get_engine()
    stmt = text(SOFT_DELETE_MESSAGE)
    params = {"p1": _as_uuid(message), "p2": None}  # deleted_at -> NOW()

    try:
        with engine.begin() as conn:
            res = conn.execute(stmt, params)
            row = res.mappings().one()
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


def GetMessage(
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

    engine = get_engine()
    stmt = text(LIST_THREAD_MESSAGES_NOT_DELETED_DESC_FIRST)
    params = {"p1": _as_uuid(thread), "p2": limit}

    try:
        with engine.begin() as conn:
            res = conn.execute(stmt, params)
            rows = res.mappings().all()
            resultado = [dict(r) for r in rows]
    except Exception as e:
        error = e

    return resultado, error
