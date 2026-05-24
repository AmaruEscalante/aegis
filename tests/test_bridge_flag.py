"""Cheap tests for the bridge --backend flag and /health endpoint."""
from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest


def test_bridge_starts_with_default_backend_local():
    """When called with no --backend arg, main() should construct a LocalBackend."""
    with patch("aegis.bridge.LocalBackend") as mock_local, \
         patch("aegis.bridge.OllamaBackend") as mock_ollama, \
         patch("aegis.bridge.HTTPServer") as mock_server, \
         patch.object(sys, "argv", ["aegis.bridge"]):
        mock_server.return_value.serve_forever.side_effect = KeyboardInterrupt()
        import aegis.bridge as aegis_bridge
        aegis_bridge.main()
    assert mock_local.called
    assert not mock_ollama.called


def test_bridge_starts_with_backend_ollama():
    """When called with --backend ollama, main() should construct OllamaBackend."""
    with patch("aegis.bridge.LocalBackend") as mock_local, \
         patch("aegis.bridge.OllamaBackend") as mock_ollama, \
         patch("aegis.bridge.HTTPServer") as mock_server, \
         patch("aegis.bridge._probe_ollama"), \
         patch.object(sys, "argv", ["aegis.bridge", "--backend", "ollama"]):
        mock_server.return_value.serve_forever.side_effect = KeyboardInterrupt()
        import aegis.bridge as aegis_bridge
        aegis_bridge.main()
    assert mock_ollama.called
    assert not mock_local.called


def test_bridge_exits_when_localbackend_init_fails(capsys):
    """If LocalBackend raises at startup, main() should exit with non-zero code."""
    with patch("aegis.bridge.LocalBackend") as mock_local, \
         patch.object(sys, "argv", ["aegis.bridge"]):
        mock_local.side_effect = RuntimeError("simulated init failure")
        import aegis.bridge as aegis_bridge
        with pytest.raises(SystemExit) as excinfo:
            aegis_bridge.main()
        assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "simulated init failure" in captured.err


def test_health_endpoint_reports_backend_type():
    """GET /health on a LocalBackend bridge returns backend=local + metadata."""
    import aegis.bridge as aegis_bridge
    # Inject a mocked LocalBackend into the module-level state.
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "LocalBackend"
    mock_backend._embed_model = "google/embeddinggemma-300m"
    mock_backend._embed_task_prompt = "classification"
    mock_backend._head_path = "aegis/head/lr.joblib"
    mock_backend._model = MagicMock()
    mock_backend._model.classes_ = ["block_transfer", "classify_safe", "flag_pii", "request_permission"]
    aegis_bridge._backend = mock_backend
    aegis_bridge._backend_name = "local"

    from http.client import HTTPConnection
    from threading import Thread
    from http.server import HTTPServer
    server = HTTPServer(("127.0.0.1", 0), aegis_bridge.BridgeHandler)
    port = server.server_port
    t = Thread(target=server.handle_request, daemon=True)
    t.start()
    try:
        conn = HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        body = json.loads(resp.read())
        assert body["backend"] == "local"
        assert body["embed_model"] == "google/embeddinggemma-300m"
        assert body["embed_task_prompt"] == "classification"
    finally:
        server.server_close()


def test_health_endpoint_includes_head_metadata_and_device():
    """Phase 3b T12 — /health on a LocalBackend bridge includes the head's C, CV F1, and device."""
    import aegis.bridge as aegis_bridge
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "LocalBackend"
    mock_backend._embed_model = "google/embeddinggemma-300m"
    mock_backend._embed_task_prompt = "none"
    mock_backend._head_path = "aegis/head/lr.joblib"
    mock_backend._head_C = 10.0
    mock_backend._head_cv_macro_f1 = 0.9799
    mock_embedder = MagicMock()
    mock_embedder.device = "mps"
    mock_backend._embedder = mock_embedder
    mock_backend._model = MagicMock()
    mock_backend._model.classes_ = ["block_transfer", "classify_safe", "flag_pii", "request_permission"]
    aegis_bridge._backend = mock_backend
    aegis_bridge._backend_name = "local"

    from http.client import HTTPConnection
    from threading import Thread
    from http.server import HTTPServer
    server = HTTPServer(("127.0.0.1", 0), aegis_bridge.BridgeHandler)
    port = server.server_port
    t = Thread(target=server.handle_request, daemon=True)
    t.start()
    try:
        conn = HTTPConnection("127.0.0.1", port)
        conn.request("GET", "/health")
        resp = conn.getresponse()
        body = json.loads(resp.read())
        assert body["head_trained_at_C"] == 10.0
        assert body["head_cv_macro_f1"] == 0.9799
        assert body["device"] == "mps"
    finally:
        server.server_close()


def test_classify_endpoint_round_trip():
    """POST /classify with mocked backend returns the expected JSON contract."""
    import aegis.bridge as aegis_bridge
    mock_backend = MagicMock()
    mock_backend.classify.return_value = {
        "tool": "block_transfer",
        "arguments": {"reason": "test"},
        "confidence": 0.95,
        "time_ms": 42.0,
    }
    aegis_bridge._backend = mock_backend
    aegis_bridge._backend_name = "local"

    from http.client import HTTPConnection
    from threading import Thread
    from http.server import HTTPServer
    server = HTTPServer(("127.0.0.1", 0), aegis_bridge.BridgeHandler)
    port = server.server_port
    t = Thread(target=server.handle_request, daemon=True)
    t.start()
    try:
        conn = HTTPConnection("127.0.0.1", port)
        conn.request(
            "POST",
            "/classify",
            body=json.dumps({"text": "AWS_SECRET_KEY=..."}),
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        body = json.loads(resp.read())
        assert body["tool"] == "block_transfer"
        assert body["confidence"] == 0.95
        assert "time_ms" in body
    finally:
        server.server_close()
