"""
Aegis Bridge — HTTP server wrapping a local Ollama model for privacy classification.

Endpoints (consumed by the TypeScript middleware and the Python CLI):
  POST /classify  — Classify a file's content into one of four verdicts
  GET  /health    — Bridge + Ollama status

Usage:
  python -m aegis.bridge                                    # defaults
  python -m aegis.bridge --model gemma4:31b --port 7523
  python -m aegis.bridge --ollama-url http://127.0.0.1:11434
"""

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import joblib
import numpy as np

from aegis.embedding import Embedder

# ── Constants ──────────────────────────────────────────────────────────────

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma4:31b"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7523
MAX_INPUT_CHARS = 8000
OLLAMA_TIMEOUT_SECONDS = 120

VERDICTS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]

# Default path to the trained LR head, relative to this package's directory.
# Resolves correctly whether the bridge is run from a dev checkout
# (cwd = repo root) or from an installed venv (cwd irrelevant).
HEAD_PATH = pathlib.Path(__file__).resolve().parent / "head" / "lr.joblib"

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": VERDICTS},
        "arguments": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "types": {"type": "string"},
            },
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["tool", "arguments", "confidence"],
}

SYSTEM_PROMPT = """You are a privacy classifier for an on-device agent system.
Given a file's contents, classify it into EXACTLY ONE of four categories by
emitting JSON matching the provided schema.

Categories:

1. classify_safe — File contains no sensitive data. Examples: public README
   files, open-source code, marketing copy, public blog posts, public metrics.
   Use `arguments.reason` to briefly describe why it's safe.

2. flag_pii — File contains personally identifiable information that can be
   redacted. Examples: emails, phone numbers, SSNs, addresses, customer
   databases, patient records, HR records. Use `arguments.types` as a
   comma-separated list from: "email,phone,ssn,address,name,date_of_birth".

3. block_transfer — File contains secrets that must NEVER be shared with cloud
   services. Examples: .env files, API keys, OAuth tokens, database
   passwords, private keys, Kubernetes secrets, docker-compose with
   credentials. Use `arguments.reason` to describe the secret type.

4. request_permission — File is ambiguous and needs human review. Examples:
   contracts, NDAs, partnership agreements, board meeting minutes, financial
   reports, internal memos, vendor evaluations, trade secrets. Use
   `arguments.reason` to explain the ambiguity.

Rules:
- Pick exactly one tool.
- Always include `confidence` in [0.0, 1.0] reflecting your certainty.
- Be conservative: if torn between classify_safe and request_permission,
  pick request_permission. If torn between flag_pii and block_transfer
  (e.g., a file contains both PII and secrets), pick block_transfer.
"""


# ── Ollama backend ─────────────────────────────────────────────────────────

class OllamaBackend:
    """One-shot classifier calling Ollama's /api/chat with JSON schema enforcement."""

    def __init__(self, ollama_url, model):
        self._ollama_url = ollama_url.rstrip("/")
        self._model = model

    def classify(self, text):
        truncated = text[:MAX_INPUT_CHARS]
        if len(text) > MAX_INPUT_CHARS:
            truncated += "\n[... file truncated ...]"

        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"File contents:\n\n{truncated}"},
            ],
            "format": CLASSIFY_SCHEMA,
            "stream": False,
            "options": {"temperature": 0.1},
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._ollama_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        start = time.time()
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read())
        elapsed_ms = (time.time() - start) * 1000

        content = data.get("message", {}).get("content", "")
        try:
            parsed = json.loads(content)
            tool = parsed["tool"]
            if tool not in VERDICTS:
                raise ValueError(f"unknown verdict: {tool}")
            args = parsed.get("arguments", {}) or {}
            confidence = float(parsed.get("confidence", 0.5))
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            return {
                "tool": "request_permission",
                "arguments": {"reason": f"Bridge could not parse model response: {e}"},
                "confidence": 0.0,
                "time_ms": elapsed_ms,
            }

        return {
            "tool": tool,
            "arguments": args,
            "confidence": confidence,
            "time_ms": elapsed_ms,
        }


# ── Local backend (Phase 3b) ───────────────────────────────────────────────

class LocalBackend:
    """In-process classifier: Embedder + LR head loaded eagerly."""

    def __init__(self, head_path: pathlib.Path = HEAD_PATH):
        if not head_path.exists():
            raise RuntimeError(
                f"No trained head at {head_path}. "
                f"Run: .venv/bin/python train/train_head.py"
            )
        bundle = joblib.load(head_path)
        self._model = bundle["model"]
        self._embed_model = bundle.get("embed_model", "")
        if "embed_task_prompt" not in bundle:
            raise RuntimeError(
                "Head was trained before task-prompt support (Phase 2 artifact). "
                "Retrain via train/train_head.py."
            )
        if "embeddinggemma" not in self._embed_model.lower():
            raise RuntimeError(
                f"Unexpected embed_model in head: {self._embed_model!r}. "
                f"Expected something containing 'embeddinggemma'."
            )
        self._embed_task_prompt = bundle["embed_task_prompt"]
        self._head_C = bundle.get("C")
        # CV macro-F1 at the chosen C — defensive lookup in case cv_results structure varies.
        self._head_cv_macro_f1 = None
        cv = bundle.get("cv_results", {})
        if self._head_C is not None and self._head_C in cv:
            self._head_cv_macro_f1 = cv[self._head_C].get("macro_f1_mean")
        self._head_path = head_path
        self._embedder = Embedder(
            model_id=self._embed_model,
            default_task=self._embed_task_prompt,
        )

    def classify(self, text: str) -> dict:
        t0 = time.perf_counter()
        try:
            vec = self._embedder.encode(text, task=self._embed_task_prompt)
            cls = self._model.predict(vec.reshape(1, -1))[0]
            probs = self._model.predict_proba(vec.reshape(1, -1))[0]
            confidence = float(probs[list(self._model.classes_).index(cls)])
            elapsed_ms = (time.perf_counter() - t0) * 1000
        except Exception as e:
            print(f"[aegis-bridge] LocalBackend classify error: {e}")
            return {
                "tool": "request_permission",
                "arguments": {"reason": f"classifier error: {type(e).__name__}"},
                "confidence": 0.0,
                "time_ms": (time.perf_counter() - t0) * 1000,
            }
        return {
            "tool": cls,
            "arguments": {"reason": f"on-device LR head ({self._embed_model})"},
            "confidence": confidence,
            "time_ms": elapsed_ms,
        }


# ── HTTP server ────────────────────────────────────────────────────────────

_backend = None
_backend_name = "unknown"  # "local" or "ollama"
_model_name = "unknown"     # ollama-specific, kept for backwards-compat /health
_ollama_url = "unknown"     # ollama-specific


class BridgeHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if self.path == "/health":
            if _backend_name == "local":
                _head_C_raw = getattr(_backend, "_head_C", None)
                _head_f1_raw = getattr(_backend, "_head_cv_macro_f1", None)
                self._send_json({
                    "status": "ok",
                    "backend": "local",
                    "embed_model": getattr(_backend, "_embed_model", "unknown"),
                    "embed_task_prompt": getattr(_backend, "_embed_task_prompt", "unknown"),
                    "head_path": str(getattr(_backend, "_head_path", "unknown")),
                    "head_classes": list(getattr(_backend._model, "classes_", [])),
                    "head_trained_at_C": float(_head_C_raw) if isinstance(_head_C_raw, (int, float)) else None,
                    "head_cv_macro_f1": float(_head_f1_raw) if isinstance(_head_f1_raw, (int, float)) else None,
                    "device": str(getattr(getattr(_backend, "_embedder", None), "device", "unknown")),
                })
            else:
                self._send_json({
                    "status": "ok",
                    "backend": "ollama",
                    "model": _model_name,
                    "ollama_url": _ollama_url,
                })
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        try:
            body = self._read_body()
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json({"error": f"invalid JSON: {e}"}, 400)
            return

        if self.path == "/classify":
            text = body.get("text", "")
            if not text:
                self._send_json({"error": "missing 'text' field"}, 400)
                return
            try:
                result = _backend.classify(text)
                self._send_json(result)
            except Exception as e:
                print(f"[aegis-bridge] /classify error: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        print(f"[aegis-bridge] {args[0]}")


def _probe_ollama(ollama_url, model):
    """Best-effort check that Ollama is running and has the model. Warn, don't fail."""
    try:
        with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=3) as resp:
            data = json.loads(resp.read())
            tags = [m["name"] for m in data.get("models", [])]
            if not any(t == model or t.startswith(f"{model}:") or t.split(":")[0] == model.split(":")[0] for t in tags):
                print(f"[aegis-bridge] WARNING: model '{model}' not found in Ollama.")
                print(f"[aegis-bridge]          Available: {', '.join(tags) or '(none)'}")
                print(f"[aegis-bridge]          Run: ollama pull {model}")
            else:
                print(f"[aegis-bridge] Ollama models available: {', '.join(tags)}")
    except urllib.error.URLError as e:
        print(f"[aegis-bridge] WARNING: could not reach Ollama at {ollama_url}: {e}")
        print(f"[aegis-bridge]          Start it with: ollama serve")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    global _backend, _backend_name, _model_name, _ollama_url

    parser = argparse.ArgumentParser(
        description="Aegis Bridge — HTTP server for on-device privacy classification",
    )
    parser.add_argument("--backend", choices=["local", "ollama"], default="local",
                        help="Which inference backend to run (default: local)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model tag, if --backend ollama (default: {DEFAULT_MODEL})")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL,
                        help=f"Ollama base URL, if --backend ollama (default: {DEFAULT_OLLAMA_URL})")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"Host to bind to (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Port to listen on (default: {DEFAULT_PORT})")

    args = parser.parse_args()

    _backend_name = args.backend

    if args.backend == "local":
        print(f"[aegis-bridge] Backend: local (in-process embeddinggemma + LR head)")
        try:
            _backend = LocalBackend()
        except Exception as e:
            print(f"[aegis-bridge] ERROR: failed to start LocalBackend: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"[aegis-bridge] Embed model: {_backend._embed_model}")
        print(f"[aegis-bridge] Task prompt: {_backend._embed_task_prompt}")
    else:
        _model_name = args.model
        _ollama_url = args.ollama_url
        print(f"[aegis-bridge] Backend: Ollama")
        print(f"[aegis-bridge] Model:   {_model_name}")
        print(f"[aegis-bridge] Ollama:  {_ollama_url}")
        _probe_ollama(_ollama_url, _model_name)
        _backend = OllamaBackend(_ollama_url, _model_name)

    server = HTTPServer((args.host, args.port), BridgeHandler)
    print(f"[aegis-bridge] Listening on http://{args.host}:{args.port}")
    print(f"[aegis-bridge] Endpoints: POST /classify, GET /health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[aegis-bridge] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
