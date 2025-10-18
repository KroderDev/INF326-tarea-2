import json
import os
from typing import Any, Dict, Optional

import pika

# Parámetros de conexión a RabbitMQ desde variables de entorno
QUEUE = {
    "user": os.getenv("QUEUE_USER", "root"),
    "password": os.getenv("QUEUE_PASSWORD", "secret"),
    "host": os.getenv("QUEUE_HOST", "localhost"),
    "port": int(os.getenv("QUEUE_PORT", "8002")),
}


def SendEvent(event_type: str, data: Dict[str, Any]) -> Optional[Exception]:
    """Publica un evento en RabbitMQ.

    - event_type: tipo de evento (e.g., CREATE)
    - data: debe contener al menos 'tag' (nombre de la cola) y 'message' (payload)
    """
    error: Optional[Exception] = None

    # Crear conexión bloqueante (mejorable con pools si es necesario)
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
            error = Exception("Unsupported event type")
    except Exception as e:  # pragma: no cover (errores de red)
        error = e
    finally:
        connection.close()
    return error
