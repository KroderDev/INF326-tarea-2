import os
from typing import TYPE_CHECKING, Optional, cast

try:
    from redis import asyncio as redis_async
except Exception:  # pragma: no cover
    redis_async = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from redis.asyncio import Redis as RedisType
else:  # pragma: no cover - solo para tipado estático

    class RedisType:  # type: ignore
        pass


_client: Optional["RedisType"] = None
_enabled: Optional[bool] = None


def cache_enabled() -> bool:
    global _enabled
    if _enabled is not None:
        return _enabled
    # Habilitado solo si la librería de redis está disponible Y hay host/url configurado
    enabled_env = os.getenv("CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}
    if redis_async is None:
        _enabled = False
        return False
    url = os.getenv("REDIS_URL")
    host = os.getenv("REDIS_HOST")
    _enabled = enabled_env and (bool(url) or bool(host))
    return _enabled


def _build_url() -> Optional[str]:
    url = os.getenv("REDIS_URL")
    if url:
        return url
    host = os.getenv("REDIS_HOST")
    if not host:
        return None
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    password = os.getenv("REDIS_PASSWORD")
    if password:
        return f"redis://:{password}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


def get_client() -> Optional["RedisType"]:
    if not cache_enabled():
        return None
    global _client
    if _client is not None:
        return _client
    assert redis_async is not None
    url = _build_url()
    if not url:
        return None
    # Pool pequeño, con timeouts conservadores para la API
    client = redis_async.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT", "0.2")),
        socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", "0.5")),
        health_check_interval=30,
    )
    _client = cast("RedisType", client)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        try:
            # Cerrar cliente de redis de manera segura
            await _client.close()  # type: ignore[attr-defined]
        finally:
            _client = None
