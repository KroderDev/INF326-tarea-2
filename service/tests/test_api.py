import importlib
import logging
import os
import sys
import uuid
from pathlib import Path

import pytest

# Ensure imports find service modules (db/, src/)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class _DummyHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def emit(self, record):
        pass

    def flush(self):
        pass


@pytest.fixture()
def api_module(monkeypatch):
    # Evita escribir logs en disco durante tests
    import logging.handlers as lh

    monkeypatch.setattr(lh, "RotatingFileHandler", _DummyHandler)
    monkeypatch.setattr(os, "makedirs", lambda *a, **k: None)

    if "API" in sys.modules:
        del sys.modules["API"]
    api = importlib.import_module("API")
    return api


def _fake_message_row(thread_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    return {
        "id": uuid.uuid4(),
        "thread_id": thread_id,
        "user_id": user_id,
        "type": None,
        "content": "hola",
        "paths": ["/a/b"],
        "created_at": None,
        "updated_at": None,
        "deleted_at": None,
    }


def test_create_message_success(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    async def _create(thread, user, content, typeM, path):
        return _fake_message_row(thread, user), None

    monkeypatch.setattr(api_module.Controller, "CreateMessage", _create)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    u = uuid.uuid4()
    r = client.post(
        f"/threads/{t}/messages",
        headers={"X-User-Id": str(u)},
        json={"content": "hola", "type": None, "paths": ["/a/b"]},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["thread_id"] == str(t)
    assert body["user_id"] == str(u)
    assert body["content"] == "hola"


def test_create_message_error_maps_500(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    async def _create(thread, user, content, typeM, path):
        return None, Exception("boom")

    monkeypatch.setattr(api_module.Controller, "CreateMessage", _create)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    u = uuid.uuid4()
    r = client.post(
        f"/threads/{t}/messages",
        headers={"X-User-Id": str(u)},
        json={"content": "hola"},
    )
    assert r.status_code == 500
    assert r.json()["detail"] == "boom"


def test_update_message_success(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    async def _update(thread, message, user, content, typeM, path):
        return (
            _fake_message_row(thread, user) | {"id": message, "content": content},
            None,
        )

    monkeypatch.setattr(api_module.Controller, "UpdateMessage", _update)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    m = uuid.uuid4()
    u = uuid.uuid4()
    r = client.put(
        f"/threads/{t}/messages/{m}",
        headers={"X-User-Id": str(u)},
        json={"content": "nuevo", "paths": None},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(m)
    assert body["content"] == "nuevo"


def test_update_message_not_found_maps_404(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    async def _update(thread, message, user, content, typeM, path):
        return None, Exception("No row returned when updating message")

    monkeypatch.setattr(api_module.Controller, "UpdateMessage", _update)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    m = uuid.uuid4()
    u = uuid.uuid4()
    r = client.put(
        f"/threads/{t}/messages/{m}",
        headers={"X-User-Id": str(u)},
        json={"content": "nuevo"},
    )
    assert r.status_code == 404


def test_delete_message_success_204(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    async def _delete(thread, message, user):
        return {"ok": True}, None

    monkeypatch.setattr(api_module.Controller, "DeleteMessage", _delete)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    m = uuid.uuid4()
    u = uuid.uuid4()
    r = client.delete(f"/threads/{t}/messages/{m}", headers={"X-User-Id": str(u)})
    assert r.status_code == 204
    assert r.text == ""


def test_delete_message_not_found_maps_404(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    async def _delete(thread, message, user):
        return None, Exception("No row returned when deleting message")

    monkeypatch.setattr(api_module.Controller, "DeleteMessage", _delete)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    m = uuid.uuid4()
    u = uuid.uuid4()
    r = client.delete(f"/threads/{t}/messages/{m}", headers={"X-User-Id": str(u)})
    assert r.status_code == 404


def test_list_messages_success(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    out = [_fake_message_row(uuid.uuid4(), uuid.uuid4())]

    async def _get(thread, typeM, filtro):
        return out, None

    monkeypatch.setattr(api_module.Controller, "GetMessage", _get)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    r = client.get(f"/threads/{t}/messages?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
