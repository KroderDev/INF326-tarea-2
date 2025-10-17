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
    # Avoid touching the filesystem under /app/logs when importing API
    import logging.handlers as lh

    monkeypatch.setattr(lh, "RotatingFileHandler", _DummyHandler)
    monkeypatch.setattr(os, "makedirs", lambda *a, **k: None)

    # Fresh import with patches applied
    if "API" in sys.modules:
        del sys.modules["API"]
    api = importlib.import_module("API")
    return api


def test_create_message_success(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    payload = {"ok": True}

    def _create(thread, user, content, typeM, path):
        return payload, None

    monkeypatch.setattr(api_module.Controller, "CreateMessage", _create)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    u = uuid.uuid4()
    r = client.post(f"/message/{t}/{u}/hola")
    assert r.status_code == 200
    assert r.json() == payload


def test_create_message_error(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    def _create(thread, user, content, typeM, path):
        return None, {"error": "boom"}

    monkeypatch.setattr(api_module.Controller, "CreateMessage", _create)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    u = uuid.uuid4()
    r = client.post(f"/message/{t}/{u}/hola")
    assert r.status_code == 200
    assert r.json() == {"error": "boom"}


def test_update_message_success(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    payload = {"updated": True}

    def _update(thread, message, user, content, typeM, path):
        return payload, None

    monkeypatch.setattr(api_module.Controller, "UpdateMessage", _update)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    m = uuid.uuid4()
    u = uuid.uuid4()
    r = client.put(f"/message/{t}/{m}/{u}/nuevo")
    assert r.status_code == 200
    assert r.json() == payload


def test_delete_message_success(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    payload = {"deleted": True}

    def _delete(message, user):
        return payload, None

    monkeypatch.setattr(api_module.Controller, "DeleteMessage", _delete)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    m = uuid.uuid4()
    u = uuid.uuid4()
    r = client.delete(f"/message/{t}/{m}/{u}")
    assert r.status_code == 200
    assert r.json() == payload


def test_get_message_success(api_module, monkeypatch):
    from fastapi.testclient import TestClient

    payload = [{"id": 1}]

    def _get(thread, typeM, filtro):
        return payload, None

    monkeypatch.setattr(api_module.Controller, "GetMessage", _get)

    client = TestClient(api_module.app)
    t = uuid.uuid4()
    r = client.get(f"/message/{t}")
    assert r.status_code == 200
    assert r.json() == payload
