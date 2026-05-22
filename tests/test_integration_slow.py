"""Slow end-to-end tests that load the real embedder + run real bridge HTTP.

Run with: .venv/bin/pytest -m slow tests/test_integration_slow.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
from http.client import HTTPConnection
from http.server import HTTPServer
from threading import Thread

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.slow


def test_localbackend_classifies_held_out_eval_above_gate():
    """Real Embedder + real head: at least 93/98 accuracy on the held-out eval set.

    The 93/98 threshold matches the Phase 3b T7f/T7g decision gate (95% accuracy
    on the held-out set). The current head was committed at this exact threshold
    in T7g (no-prompt rollback).
    """
    import aegis_bridge
    from eval import CASES

    backend = aegis_bridge.LocalBackend()
    correct = 0
    for path, expected in CASES:
        text = pathlib.Path(path).read_text()
        result = backend.classify(text)
        if result["tool"] == expected:
            correct += 1
    assert correct >= 93, f"regression: {correct}/{len(CASES)} (Phase 3b T7g gate was 93/98)"


def test_bridge_real_local_serves_held_out_eval_above_gate():
    """Bring up the real bridge in-process and POST each of the 98 CASES."""
    import aegis_bridge
    from eval import CASES

    aegis_bridge._backend = aegis_bridge.LocalBackend()
    aegis_bridge._backend_name = "local"

    server = HTTPServer(("127.0.0.1", 0), aegis_bridge.BridgeHandler)
    port = server.server_port
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()

    try:
        correct = 0
        latencies = []
        for path, expected in CASES:
            text = pathlib.Path(path).read_text()
            conn = HTTPConnection("127.0.0.1", port)
            start = time.perf_counter()
            conn.request(
                "POST",
                "/classify",
                body=json.dumps({"text": text}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            body = json.loads(resp.read())
            latencies.append((time.perf_counter() - start) * 1000)
            if body["tool"] == expected:
                correct += 1
        # Drop the very first call (HTTP roundtrip cold-start artifact).
        warm = sorted(latencies[1:])
        p50 = warm[len(warm) // 2]
    finally:
        server.shutdown()
        server.server_close()

    assert correct >= 93, f"regression: {correct}/{len(CASES)} (Phase 3b T7g gate was 93/98)"
    # Latency tolerance: target ≤200ms, accept ≤400ms on CPU/MPS (training-time variation).
    assert p50 <= 400, f"warm p50 too high: {p50:.0f}ms (target ≤200ms; ≤400ms tolerated)"
