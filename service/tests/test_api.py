import datetime
import importlib
import logging
import logging.handlers as lh
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

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


def test_create_message_invalid_user_header_returns_400(api_module, monkeypatch):

    called = {"value": False}

    async def _create(thread, user, content, typeM, path):
        called["value"] = True
        return None, None

    monkeypatch.setattr(api_module.Controller, "CreateMessage", _create)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    r = client.post(
        f"/threads/{t}/messages",
        headers={"X-User-Id": "not-a-uuid"},
        json={"content": "hola"},
    )
    assert r.status_code == 400
    assert "hexadecimal" in r.json()["detail"]
    assert not called["value"]


def test_create_message_invalidates_cache(api_module, monkeypatch):

    async def _create(thread, user, content, typeM, path):
        return _fake_message_row(thread, user), None

    captured = {}

    async def _invalidate(thread_id):
        captured["thread"] = thread_id

    monkeypatch.setattr(api_module.Controller, "CreateMessage", _create)
    monkeypatch.setattr(api_module.cache_recent, "invalidate_thread", _invalidate)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    u = uuid.uuid4()
    r = client.post(
        f"/threads/{t}/messages",
        headers={"X-User-Id": str(u)},
        json={"content": "hola"},
    )
    assert r.status_code == 201
    assert captured["thread"] == str(t)


def test_update_message_success(api_module, monkeypatch):

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


def test_update_message_invalidates_cache(api_module, monkeypatch):

    async def _update(thread, message, user, content, typeM, path):
        return (
            _fake_message_row(thread, user) | {"id": message, "content": content},
            None,
        )

    captured = {}

    async def _invalidate(thread_id):
        captured["thread"] = thread_id

    monkeypatch.setattr(api_module.Controller, "UpdateMessage", _update)
    monkeypatch.setattr(api_module.cache_recent, "invalidate_thread", _invalidate)

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
    assert captured["thread"] == str(t)


def test_update_message_not_found_maps_404(api_module, monkeypatch):

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


def test_delete_message_invalidates_cache(api_module, monkeypatch):

    async def _delete(thread, message, user):
        return {"ok": True}, None

    captured = {}

    async def _invalidate(thread_id):
        captured["thread"] = thread_id

    monkeypatch.setattr(api_module.Controller, "DeleteMessage", _delete)
    monkeypatch.setattr(api_module.cache_recent, "invalidate_thread", _invalidate)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    m = uuid.uuid4()
    u = uuid.uuid4()
    r = client.delete(f"/threads/{t}/messages/{m}", headers={"X-User-Id": str(u)})
    assert r.status_code == 204
    assert captured["thread"] == str(t)


def test_delete_message_not_found_maps_404(api_module, monkeypatch):

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

    out = [_fake_message_row(uuid.uuid4(), uuid.uuid4())]

    async def _get(thread, typeM, filtro):
        return out, None

    monkeypatch.setattr(api_module.Controller, "ListMessages", _get)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    r = client.get(f"/threads/{t}/messages?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert isinstance(body["items"], list)
    assert body.get("next_cursor") is None or isinstance(body.get("next_cursor"), str)
    assert body.get("has_more") in {True, False}


def test_list_messages_invalid_cursor_returns_400(api_module, monkeypatch):

    async def _list(*args, **kwargs):
        raise AssertionError("ListMessages should not run on invalid cursor")

    monkeypatch.setattr(api_module.Controller, "ListMessages", _list)
    monkeypatch.setattr(api_module.Controller, "ListMessagesBefore", _list)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    r = client.get(f"/threads/{t}/messages?cursor=not-a-valid-cursor")
    assert r.status_code == 400


def test_list_messages_cursor_calls_before(api_module, monkeypatch):

    out = [_fake_message_row(uuid.uuid4(), uuid.uuid4())]
    ts = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
    mid = uuid.uuid4()
    raw_cursor = f"{ts.isoformat()}|{mid}"
    cursor = quote(raw_cursor, safe="")

    async def _before(thread, created_at, message_id, limit):
        assert thread == thread_id
        assert created_at == ts
        assert message_id == mid
        assert limit == 15
        return out, None

    async def _list(*args, **kwargs):
        raise AssertionError("ListMessages should not run when cursor provided")

    thread_id = uuid.uuid4()
    monkeypatch.setattr(api_module.Controller, "ListMessagesBefore", _before)
    monkeypatch.setattr(api_module.Controller, "ListMessages", _list)

    client = TestClient(api_module.app)
    r = client.get(f"/threads/{thread_id}/messages?cursor={cursor}&limit=15")
    assert r.status_code == 200
    assert r.json()["items"][0]["id"] == str(out[0]["id"])


def test_list_messages_cache_hit_shortcircuits_controller(api_module, monkeypatch):

    thread_id = uuid.uuid4()
    cached = [_fake_message_row(uuid.uuid4(), uuid.uuid4())]

    async def _get_recent(thread, limit):
        assert thread == str(thread_id)
        assert limit == 5
        return cached

    async def _set_recent(*args, **kwargs):
        raise AssertionError("set_recent_messages should not be called on hit")

    async def _list(*args, **kwargs):
        raise AssertionError("DB should not be hit on cache hit")

    monkeypatch.setattr(api_module.cache_recent, "get_recent_messages", _get_recent)
    monkeypatch.setattr(api_module.cache_recent, "set_recent_messages", _set_recent)
    monkeypatch.setattr(api_module.Controller, "ListMessages", _list)

    client = TestClient(api_module.app)
    r = client.get(f"/threads/{thread_id}/messages?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(cached[0]["id"])


def test_list_messages_sets_cache_after_db_fetch(api_module, monkeypatch):

    out = [_fake_message_row(uuid.uuid4(), uuid.uuid4())]
    set_args = {}

    async def _get_recent(thread, limit):
        return None

    async def _set_recent(thread, items):
        set_args["thread"] = thread
        set_args["items"] = items

    async def _list(thread, typeM, filtro):
        assert typeM == 1
        assert filtro == "25"
        return out, None

    monkeypatch.setattr(api_module.cache_recent, "get_recent_messages", _get_recent)
    monkeypatch.setattr(api_module.cache_recent, "set_recent_messages", _set_recent)
    monkeypatch.setattr(api_module.Controller, "ListMessages", _list)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    r = client.get(f"/threads/{t}/messages?limit=25")
    assert r.status_code == 200
    assert set_args["thread"] == str(t)
    assert set_args["items"][0]["id"] == out[0]["id"]
