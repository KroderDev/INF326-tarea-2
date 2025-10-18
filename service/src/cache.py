import json
import logging
import os
from typing import Any, Dict, List, Optional

from clients.redis import cache_enabled, get_client

try:
    import orjson  # type: ignore
except Exception:  # pragma: no cover - opcional
    orjson = None  # type: ignore


CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "120"))
CACHE_MAX_ITEMS = int(os.getenv("CACHE_MAX_ITEMS", "200"))
CACHE_TOUCH_ON_HIT = os.getenv("CACHE_TOUCH_ON_HIT", "true").lower() in {
    "1",
    "true",
    "yes",
}


def _key_recent(thread_id: str) -> str:
    return f"messages:thread:{thread_id}:recent"


def _dumps(obj: Any) -> str:
    # Serializar convirtiendo tipos no estándar (UUID, datetime, enums) a str
    if orjson is not None:
        return orjson.dumps(obj, default=lambda x: str(x)).decode("utf-8")
    return json.dumps(obj, separators=(",", ":"), default=str)


def _loads(s: str) -> Any:
    if orjson is not None:
        return orjson.loads(s)
    return json.loads(s)


async def get_recent_messages(
    thread_id: str, limit: int
) -> Optional[List[Dict[str, Any]]]:
    if not cache_enabled():
        return None
    client = get_client()
    if client is None:
        return None
    try:
        val = await client.get(_key_recent(thread_id))
        if val is None:
            return None
        data = _loads(val)
        if not isinstance(data, list):
            return None
        if CACHE_TOUCH_ON_HIT and CACHE_TTL_SECONDS > 0:
            await client.expire(_key_recent(thread_id), CACHE_TTL_SECONDS)
        return data[:limit]
    except Exception as e:
        # Log en WARN si falla redis al obtener
        logging.getLogger("API_logs").warning(
            f"Cache get error thread={thread_id} err={e.__class__.__name__}:{e}"
        )
        return None


async def set_recent_messages(thread_id: str, items: List[Dict[str, Any]]) -> None:
    if not cache_enabled():
        return
    client = get_client()
    if client is None:
        return
    try:
        trimmed = items[:CACHE_MAX_ITEMS]
        payload = _dumps(trimmed)
        if CACHE_TTL_SECONDS > 0:
            await client.set(_key_recent(thread_id), payload, ex=CACHE_TTL_SECONDS)
        else:
            await client.set(_key_recent(thread_id), payload)
    except Exception as e:
        # mejor esfuerzo
        logging.getLogger("API_logs").warning(
            f"Cache set error thread={thread_id} items={len(items)} err={e.__class__.__name__}:{e}"
        )
        return


async def invalidate_thread(thread_id: str) -> None:
    if not cache_enabled():
        return
    client = get_client()
    if client is None:
        return
    try:
        await client.delete(_key_recent(thread_id))
    except Exception as e:
        logging.getLogger("API_logs").warning(
            f"Cache invalidate error thread={thread_id} err={e.__class__.__name__}:{e}"
        )
        return
