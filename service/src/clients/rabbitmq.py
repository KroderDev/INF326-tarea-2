import json
import os
import time
from typing import Any, Dict, Optional

import pika

try:
    # Opcional: usamos Redis como outbox en caso de caída del broker
    from . import redis as redis_client  # relative import dentro de clients/
except Exception:  # pragma: no cover - redis es opcional
    redis_client = None  # type: ignore


def _queue_enabled() -> bool:
    # Permite deshabilitar el broker sin cambiar código
    return os.getenv("QUEUE_ENABLED", "true").lower() in {"1", "true", "yes"}


def _queue_params() -> Dict[str, Any]:
    # Parámetros conservadores para no bloquear la API si el broker no responde
    return {
        "user": os.getenv("QUEUE_USER", "root"),
        "password": os.getenv("QUEUE_PASSWORD", "secret"),
        "host": os.getenv("QUEUE_HOST", "localhost"),
        "port": int(os.getenv("QUEUE_PORT", "8002")),
        # timeouts/bounds
        "connection_attempts": int(os.getenv("QUEUE_CONN_ATTEMPTS", "1")),
        "retry_delay": float(os.getenv("QUEUE_RETRY_DELAY", "0.2")),
        "socket_timeout": float(os.getenv("QUEUE_SOCKET_TIMEOUT", "0.5")),
        "blocked_connection_timeout": float(os.getenv("QUEUE_BLOCKED_TIMEOUT", "0.5")),
        "heartbeat": int(os.getenv("QUEUE_HEARTBEAT", "30")),
    }


def _outbox_enabled() -> bool:
    # Almacena eventos para reintento asíncrono (vía Redis) si falla el broker
    return os.getenv("QUEUE_OUTBOX_REDIS_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
    }


async def _save_to_outbox_redis(event_type: str, data: Dict[str, Any]) -> None:
    if not _outbox_enabled():
        return
    if redis_client is None or not hasattr(redis_client, "get_client"):
        return
    client = redis_client.get_client()
    if client is None:
        return
    try:
        payload = {
            "ts": int(time.time()),
            "event_type": event_type,
            "data": data,
        }
        key = os.getenv("QUEUE_OUTBOX_REDIS_KEY", "outbox:rabbitmq:messages")
        # Guardar como JSON en una lista (cola FIFO)
        await client.rpush(key, json.dumps(payload, default=str))  # type: ignore[attr-defined]
        # Establecer TTL opcional para evitar crecimiento infinito
        ttl = int(os.getenv("QUEUE_OUTBOX_TTL_SECONDS", "0"))
        if ttl > 0:
            await client.expire(key, ttl)  # type: ignore[attr-defined]
    except Exception:
        # Mejor esfuerzo: si falla el outbox no interrumpimos la API
        return


def SendEvent(event_type: str, data: Dict[str, Any]) -> Optional[Exception]:
    """Publica un evento en RabbitMQ de forma best-effort.

    - Nunca levanta una excepción: ante cualquier error devuelve la excepción y
      deja que la API continúe para no impactar en el path crítico.
    - Puede usar un outbox en Redis si está habilitado para reintentos offline.
    - `data` debe contener 'tag' (cola) y 'message' (payload JSON-serializable).
    """
    if not _queue_enabled():
        return None

    error: Optional[Exception] = None
    params = _queue_params()
    connection = None
    channel = None

    try:
        credentials = pika.PlainCredentials(params["user"], params["password"])
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=params["host"],
                port=params["port"],
                credentials=credentials,
                heartbeat=params["heartbeat"],
                blocked_connection_timeout=params["blocked_connection_timeout"],
                connection_attempts=params["connection_attempts"],
                retry_delay=params["retry_delay"],
                socket_timeout=params["socket_timeout"],
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue=data["tag"], durable=True)

        if event_type == "CREATE":
            body = json.dumps(data["message"], default=str)
            channel.basic_publish(
                exchange="",
                routing_key=data["tag"],
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
        else:
            error = Exception("Unsupported event type")
    except Exception as e:  # pragma: no cover - dependencias externas
        error = e
    finally:
        try:
            if connection is not None:
                connection.close()
        except Exception:
            pass

    # Fallback a outbox si falló la publicación
    if error is not None:
        try:
            import asyncio

            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and not loop.is_closed():
                # Ejecutar async sin bloquear el hilo actual
                loop.create_task(_save_to_outbox_redis(event_type, data))
            else:
                # Si estamos fuera de un loop, crear uno corto
                asyncio.run(_save_to_outbox_redis(event_type, data))
        except Exception:
            pass

    return error
