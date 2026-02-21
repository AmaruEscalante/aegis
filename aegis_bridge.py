"""
Aegis Bridge — HTTP server wrapping FunctionGemma classification via Cactus or Transformers.

Provides three endpoints consumed by the TypeScript middleware:
  POST /summarize  — Summarize file text locally (on-device)
  POST /classify   — Classify sensitivity of a file summary
  GET  /health     — Check bridge status and backend info

Usage:
  python aegis_bridge.py --backend cactus                                  # default
  python aegis_bridge.py --backend transformers --model ./aegis-adapter
  python aegis_bridge.py --port 7523

The TypeScript middleware calls this bridge over localhost. Both backends return
identical JSON response shapes so the middleware doesn't need to know which is active.
"""

import argparse
import json
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Shared constants (same as aegis.py) ────────────────────────────────────

PRIVACY_TOOLS = [
    {
        "name": "classify_safe",
        "description": "The file content is safe to share with cloud AI. No sensitive data detected.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Brief reason why the file is safe",
                }
            },
            "required": ["reason"],
        },
    },
    {
        "name": "flag_pii",
        "description": "The file contains personally identifiable information (PII) like emails, phone numbers, social security numbers, or addresses that must be redacted before sharing.",
        "parameters": {
            "type": "object",
            "properties": {
                "types": {
                    "type": "string",
                    "description": "Comma-separated list of PII types found: email, ssn, phone, address, name",
                }
            },
            "required": ["types"],
        },
    },
    {
        "name": "block_transfer",
        "description": "The file contains secrets, API keys, passwords, database credentials, or encryption keys. It must NEVER be sent to the cloud.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why the file must be blocked from transfer",
                }
            },
            "required": ["reason"],
        },
    },
    {
        "name": "request_permission",
        "description": "The file contains ambiguous or potentially confidential content like trade secrets, internal project names, legal terms, or financial details. Need human approval before sharing.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "What is ambiguous and why human review is needed",
                }
            },
            "required": ["reason"],
        },
    },
]

SYSTEM_MSG = "You are a privacy classifier. Based on the file summary, call the correct tool."
LABELS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]

SUMMARIZER_SYSTEM_PROMPT = (
    "You are a file security scanner. Summarize the file content in 2-3 sentences. "
    "Then list ANY potentially sensitive information you notice: "
    "personal names, email addresses, phone numbers, social security numbers, "
    "API keys, passwords, database credentials, encryption keys, "
    "confidential project names, trade secrets, financial figures, or legal terms. "
    "Be specific about what you found."
)


# ── Tool-call response parser ──────────────────────────────────────────────

def parse_tool_call(response_text):
    """Extract tool name and arguments from a FunctionGemma response.

    Handles the call:tool_name{key: <escape>value<escape>, ...} format produced
    by both Cactus and Transformers inference.

    Returns (tool_name, arguments_dict).
    """
    for label in LABELS:
        marker = f"call:{label}"
        if marker not in response_text:
            continue

        args = {}
        try:
            call_start = response_text.index(marker) + len(marker)
            rest = response_text[call_start:]
            if rest.lstrip().startswith("{"):
                brace_start = rest.index("{")
                brace_end = rest.index("}", brace_start)
                args_str = rest[brace_start + 1:brace_end]
                for part in args_str.split(","):
                    part = part.strip()
                    if ":" in part:
                        k, v = part.split(":", 1)
                        v = v.strip().replace("<escape>", "").strip()
                        if v:
                            args[k.strip()] = v
        except (ValueError, IndexError):
            pass

        # Fill sensible defaults when args are missing
        if not args:
            if label == "flag_pii":
                args = {"types": "email,phone,ssn"}
            else:
                args = {"reason": f"classified as {label}"}

        return label, args

    return "request_permission", {"reason": "Unable to classify — requesting human review"}


# ── Backend: Cactus SDK ────────────────────────────────────────────────────

class CactusBackend:
    """Inference backend using the Cactus on-device runtime."""

    def __init__(self, model_path, summarizer_path=None):
        sys.path.insert(0, "cactus/python/src")
        from cactus import cactus_init, cactus_complete, cactus_destroy
        self._init = cactus_init
        self._complete = cactus_complete
        self._destroy = cactus_destroy
        self._model_path = model_path
        self._summarizer_path = summarizer_path

    def classify(self, summary):
        """Classify a file summary using FunctionGemma via Cactus."""
        model = self._init(self._model_path)
        cactus_tools = [{"type": "function", "function": t} for t in PRIVACY_TOOLS]
        messages = [
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": f"File summary:\n{summary}"},
        ]

        start = time.time()
        raw_str = self._complete(
            model, messages,
            tools=cactus_tools,
            force_tools=True,
            max_tokens=256,
            confidence_threshold=0.0,
            stop_sequences=["<|im_end|>", "<end_of_turn>"],
        )
        elapsed_ms = (time.time() - start) * 1000
        self._destroy(model)

        tool_name = "request_permission"
        tool_args = {"reason": "Unable to classify — requesting human review"}
        confidence = 0.0

        try:
            raw = json.loads(raw_str)
            confidence = raw.get("confidence", 0)
            function_calls = raw.get("function_calls", [])
            resp_text = raw.get("response", "") or ""

            if function_calls:
                tool_name = function_calls[0].get("name", "request_permission")
                tool_args = function_calls[0].get("arguments", {})
            elif resp_text:
                tool_name, tool_args = parse_tool_call(resp_text)
        except (json.JSONDecodeError, TypeError):
            raw_text = str(raw_str) if raw_str else ""
            tool_name, tool_args = parse_tool_call(raw_text)

        return {
            "tool": tool_name,
            "arguments": tool_args,
            "confidence": confidence,
            "time_ms": elapsed_ms,
        }

    def summarize(self, text):
        """Summarize file text using on-device Gemma-3-1B via Cactus."""
        if not self._summarizer_path:
            return {"summary": text[:2000], "time_ms": 0}

        model = self._init(self._summarizer_path)
        messages = [
            {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Scan this file:\n\n{text[:8000]}"},
        ]
        start = time.time()
        raw_str = self._complete(
            model, messages,
            max_tokens=300,
            temperature=0.3,
            stop_sequences=["<|im_end|>", "<end_of_turn>"],
        )
        elapsed_ms = (time.time() - start) * 1000
        self._destroy(model)

        try:
            raw = json.loads(raw_str)
            summary = raw.get("response", "") or ""
        except (json.JSONDecodeError, TypeError):
            summary = str(raw_str) if raw_str else ""

        return {"summary": summary or text[:2000], "time_ms": elapsed_ms}


# ── Backend: HuggingFace Transformers ──────────────────────────────────────

class TransformersBackend:
    """Inference backend using HuggingFace Transformers (AutoModelForCausalLM).

    Loads the model once at startup and keeps it warm in GPU/CPU memory.
    Uses the same apply_chat_template + greedy decode pattern as
    model-merge/merge_and_test.py.
    """

    def __init__(self, model_path):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        self._torch = torch
        print(f"[aegis-bridge] Loading model from {model_path} ...")
        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            attn_implementation="eager",
        )
        self._model.eval()
        print(f"[aegis-bridge] Model loaded on {self._model.device}")

        # Wrap tools for apply_chat_template format
        self._tools = [{"type": "function", "function": t} for t in PRIVACY_TOOLS]

    def classify(self, summary):
        """Classify a file summary using FunctionGemma via Transformers.

        Uses "developer" role (Gemma chat template convention) and greedy
        decoding, matching the pattern in model-merge/merge_and_test.py.
        """
        messages = [
            {"role": "developer", "content": SYSTEM_MSG},
            {"role": "user", "content": f"File summary:\n{summary}"},
        ]

        inputs = self._tokenizer.apply_chat_template(
            messages,
            tools=self._tools,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )

        start = time.time()
        with self._torch.no_grad():
            out = self._model.generate(
                **inputs.to(self._model.device),
                pad_token_id=self._tokenizer.eos_token_id,
                max_new_tokens=128,
                do_sample=False,
            )
        elapsed_ms = (time.time() - start) * 1000

        response = self._tokenizer.decode(
            out[0][len(inputs["input_ids"][0]):],
            skip_special_tokens=False,
        )

        tool_name, tool_args = parse_tool_call(response)

        # Transformers backend doesn't provide a native confidence score.
        # Use 1.0 for recognised labels; 0.5 for the fallback (request_permission).
        confidence = 1.0 if tool_name != "request_permission" else 0.5

        return {
            "tool": tool_name,
            "arguments": tool_args,
            "confidence": confidence,
            "time_ms": elapsed_ms,
        }

    def summarize(self, text):
        """Return a truncated excerpt as the summary.

        FunctionGemma-270M is a tool-calling model, not a summarizer.
        For the Transformers backend we return truncated text; full
        summarization requires a separate model (e.g., Gemma-3-1B via Cactus).
        """
        truncated = text[:2000]
        return {"summary": truncated, "time_ms": 0}


# ── HTTP Server ────────────────────────────────────────────────────────────

_backend = None   # Set at startup
_backend_name = "unknown"
_model_name = "unknown"


class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Aegis bridge."""

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
            self._send_json({
                "status": "ok",
                "backend": _backend_name,
                "model": _model_name,
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
            summary = body.get("summary", "")
            if not summary:
                self._send_json({"error": "missing 'summary' field"}, 400)
                return
            try:
                result = _backend.classify(summary)
                self._send_json(result)
            except Exception as e:
                print(f"[aegis-bridge] /classify error: {e}")
                self._send_json({"error": str(e)}, 500)

        elif self.path == "/summarize":
            text = body.get("text", "")
            if not text:
                self._send_json({"error": "missing 'text' field"}, 400)
                return
            try:
                result = _backend.summarize(text)
                self._send_json(result)
            except Exception as e:
                print(f"[aegis-bridge] /summarize error: {e}")
                self._send_json({"error": str(e)}, 500)

        else:
            self._send_json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        """Override to add prefix and reduce noise."""
        print(f"[aegis-bridge] {args[0]}")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    global _backend, _backend_name, _model_name

    parser = argparse.ArgumentParser(
        description="Aegis Bridge — HTTP server for FunctionGemma classification",
    )
    parser.add_argument(
        "--backend", choices=["cactus", "transformers"], default="cactus",
        help="Inference backend (default: cactus)",
    )
    parser.add_argument(
        "--model", default=None,
        help="Path to classifier model (default: auto per backend)",
    )
    parser.add_argument(
        "--summarizer", default=None,
        help="Path to summarizer model (Cactus backend only; default: cactus/weights/gemma-3-1b-it)",
    )
    parser.add_argument(
        "--port", type=int, default=7523,
        help="Port to listen on (default: 7523)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )

    args = parser.parse_args()
    _backend_name = args.backend

    if args.backend == "cactus":
        model_path = args.model or "cactus/weights/aegis-adapter"
        summarizer_path = args.summarizer or "cactus/weights/gemma-3-1b-it"
        _model_name = model_path
        print(f"[aegis-bridge] Backend: Cactus SDK")
        print(f"[aegis-bridge] Classifier model: {model_path}")
        print(f"[aegis-bridge] Summarizer model: {summarizer_path}")
        _backend = CactusBackend(model_path, summarizer_path)

    elif args.backend == "transformers":
        model_path = args.model or "aegis-adapter"
        _model_name = model_path
        print(f"[aegis-bridge] Backend: HuggingFace Transformers")
        print(f"[aegis-bridge] Classifier model: {model_path}")
        _backend = TransformersBackend(model_path)

    server = HTTPServer((args.host, args.port), BridgeHandler)
    print(f"[aegis-bridge] Listening on http://{args.host}:{args.port}")
    print(f"[aegis-bridge] Endpoints: POST /classify, POST /summarize, GET /health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[aegis-bridge] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
