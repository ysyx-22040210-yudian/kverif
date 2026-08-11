from __future__ import annotations

import importlib.util
import json
import socket
import threading
from pathlib import Path

import pytest


def _load_engine(kdebug_root: Path):
    path = kdebug_root / "tcl_engine" / "kdebug_engine.py"
    spec = importlib.util.spec_from_file_location("kdebug_engine_transport_scale", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.contract
def test_uds_reader_receives_large_port_request_in_chunks(kdebug_root: Path) -> None:
    engine = _load_engine(kdebug_root)
    request = {
        "api_version": engine.INTERNAL_API_VERSION,
        "action": "port.trace_batch",
        "target": {"session_id": "scale"},
        "args": {
            "module": "Dispatch",
            "ports": ["port_%05d" % index for index in range(50000)],
        },
    }
    payload = (json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8")
    assert len(payload) > 500000

    reader, writer = socket.socketpair()
    recv_calls = []

    class CountingSocket:
        def recv(self, size):
            recv_calls.append(size)
            return reader.recv(size)

    sender_error = []

    def send_payload():
        try:
            writer.sendall(payload)
        except BaseException as exc:  # pragma: no cover - diagnostic only
            sender_error.append(exc)
        finally:
            writer.close()

    sender = threading.Thread(target=send_payload)
    sender.start()
    try:
        received = engine.read_line(CountingSocket())
    finally:
        reader.close()
    sender.join(timeout=10)

    assert not sender.is_alive()
    assert not sender_error
    assert json.loads(received) == request
    assert recv_calls
    assert set(recv_calls) == {engine.SOCKET_READ_CHUNK_BYTES}
    assert len(recv_calls) < 100


@pytest.mark.contract
def test_session_default_timeout_matches_npi_default(
    kdebug_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _load_engine(kdebug_root)
    observed = {}

    def fake_send(record, request, timeout_ms):
        observed["timeout_ms"] = timeout_ms
        return {"ok": True, "data": {}}

    monkeypatch.setattr(engine, "send_to_uds", fake_send)
    result = engine.route_to_session(
        {"transport": "uds", "socket_path": "/tmp/unused.sock"},
        {"action": "server.ping"},
    )

    assert result["ok"] is True
    assert engine.DEFAULT_NPI_TIMEOUT_MS == 120000
    assert observed["timeout_ms"] == engine.DEFAULT_NPI_TIMEOUT_MS
