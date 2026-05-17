# Ollama Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Cactus + FunctionGemma + LM Studio + SmolLM2 inference stack with a single Ollama call running stock Gemma 4 E2B, while preserving the four-verdict semantics and the downstream DataGuard pipeline.

**Architecture:** One Python HTTP bridge (~200 lines) wrapping Ollama's `/api/chat` with JSON-schema-enforced structured output. The bridge keeps the same `POST /classify` response shape but drops `POST /summarize` entirely. Middleware and backend lose their summarize calls; everything else downstream is untouched.

**Tech Stack:** Python 3.12 (stdlib only — `http.server`, `urllib.request`, `json`), TypeScript + Vitest (middleware), FastAPI + httpx (backend), Ollama 0.5+ (for `format: <schema>` structured output), Gemma 4 E2B model.

**Spec:** `docs/superpowers/specs/2026-05-12-ollama-migration-design.md`

**Branch:** `ollama-migration` (do not merge to main without teammate sign-off)

---

### Task 1: Verify Ollama and pull the model

**Files:** None (environment setup)

- [ ] **Step 1: Confirm Ollama is installed**

Run: `ollama --version`

Expected: prints a version number (require ≥ 0.5.0 for JSON schema `format` support).

If not installed: `brew install ollama` (macOS) then `ollama serve` in a separate terminal, OR install via https://ollama.com/download.

- [ ] **Step 2: Verify Ollama daemon is running**

Run: `curl -sf http://127.0.0.1:11434/api/tags > /dev/null && echo OK || echo "Ollama not running"`

Expected: `OK`. If "Ollama not running", run `ollama serve` in another terminal.

- [ ] **Step 3: Pull the model**

Run: `ollama pull gemma4:e2b`

Expected: download completes (~1.5 GB).

- [ ] **Step 4: Smoke-test the model with structured output**

Run:
```bash
curl -s http://127.0.0.1:11434/api/chat -d '{
  "model": "gemma4:e2b",
  "messages": [{"role":"user","content":"Reply with JSON: {\"ok\": true}"}],
  "format": {"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"]},
  "stream": false
}' | python3 -c "import sys, json; r = json.load(sys.stdin); print(r['message']['content'])"
```

Expected: prints `{"ok": true}` or similar valid JSON matching the schema. If the model returns prose, structured output isn't working — upgrade Ollama.

---

### Task 2: Write the failing bridge smoke test

**Files:**
- Create: `test_bridge_smoke.py` (repo root)

- [ ] **Step 1: Write the smoke test script**

Create `test_bridge_smoke.py`:

```python
"""
End-to-end smoke test for the Ollama-backed Aegis bridge.

Starts no server itself — assumes `python aegis_bridge.py` is already running
on http://127.0.0.1:7523 and Ollama has `gemma4:e2b` pulled.

Exercises all 4 verdict categories against the sample files. Exits 0 on
success, 1 on any classification mismatch or transport error.
"""

import json
import sys
import time
import urllib.error
import urllib.request

BRIDGE_URL = "http://127.0.0.1:7523"

# Sample file → expected verdict (the tool name returned by /classify)
CASES = [
    ("samples/open_source_readme.md",   "classify_safe"),
    ("samples/marketing_copy.txt",      "classify_safe"),
    ("samples/patient_records.csv",     "flag_pii"),
    ("samples/employee_directory.json", "flag_pii"),
    ("samples/api_config.env",          "block_transfer"),
    ("samples/kubernetes_secrets.yaml", "block_transfer"),
    ("samples/vendor_evaluation.txt",   "request_permission"),
    ("samples/partnership_agreement.txt", "request_permission"),
]


def post_classify(text):
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{BRIDGE_URL}/classify",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def get_health():
    with urllib.request.urlopen(f"{BRIDGE_URL}/health", timeout=3) as resp:
        return json.loads(resp.read())


def main():
    try:
        health = get_health()
    except urllib.error.URLError as e:
        print(f"FAIL: bridge unreachable at {BRIDGE_URL}: {e}")
        print("Start it with: python aegis_bridge.py")
        sys.exit(1)

    print(f"Bridge health: {health}")
    assert health.get("status") == "ok", f"bridge not ok: {health}"

    failures = 0
    for path, expected_tool in CASES:
        try:
            with open(path, "r", errors="replace") as f:
                content = f.read()
        except OSError as e:
            print(f"SKIP {path}: {e}")
            continue

        start = time.time()
        result = post_classify(content)
        wall_ms = (time.time() - start) * 1000

        actual_tool = result.get("tool")
        confidence = result.get("confidence", 0)
        status = "OK  " if actual_tool == expected_tool else "FAIL"
        if actual_tool != expected_tool:
            failures += 1
        print(
            f"  [{status}] {path:42s} expected={expected_tool:20s} "
            f"got={actual_tool:20s} conf={confidence:.2f} ({wall_ms:.0f}ms)"
        )

    if failures:
        print(f"\n{failures} failure(s) out of {len(CASES)} cases")
        sys.exit(1)

    print(f"\nAll {len(CASES)} cases passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it to verify it fails (bridge not yet rewritten)**

Run: `python test_bridge_smoke.py`

Expected outcome depends on whether the old bridge is currently running:
- If old bridge is NOT running: `FAIL: bridge unreachable` — this is the expected starting state.
- If old bridge IS running with Cactus/Transformers: it accepts `{summary: ...}` not `{text: ...}` on `/classify`, so requests will fail with `missing 'summary' field` (HTTP 400). Either way, the test fails as expected.

Either failure mode confirms we have a "red" test before the rewrite. Don't proceed unless the test fails.

- [ ] **Step 3: Commit**

```bash
git add test_bridge_smoke.py
git commit -m "Add Ollama bridge smoke test (red phase)"
```

---

### Task 3: Rewrite `aegis_bridge.py` with OllamaBackend

**Files:**
- Modify: `aegis_bridge.py` (full rewrite, ~530 → ~200 lines)

- [ ] **Step 1: Replace the entire file**

Overwrite `aegis_bridge.py` with this:

```python
"""
Aegis Bridge — HTTP server wrapping a local Ollama model for privacy classification.

Endpoints (consumed by the TypeScript middleware and the Python CLI):
  POST /classify  — Classify a file's content into one of four verdicts
  GET  /health    — Bridge + Ollama status

Usage:
  python aegis_bridge.py                                    # defaults
  python aegis_bridge.py --model gemma4:e2b --port 7523
  python aegis_bridge.py --ollama-url http://127.0.0.1:11434
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── Constants ──────────────────────────────────────────────────────────────

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma4:e2b"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7523
MAX_INPUT_CHARS = 8000
OLLAMA_TIMEOUT_SECONDS = 60

VERDICTS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]

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


# ── HTTP server ────────────────────────────────────────────────────────────

_backend = None
_model_name = "unknown"
_ollama_url = "unknown"


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
    global _backend, _model_name, _ollama_url

    parser = argparse.ArgumentParser(
        description="Aegis Bridge — HTTP server for Ollama-backed privacy classification",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model tag (default: {DEFAULT_MODEL})")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL,
                        help=f"Ollama base URL (default: {DEFAULT_OLLAMA_URL})")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"Host to bind to (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Port to listen on (default: {DEFAULT_PORT})")

    args = parser.parse_args()

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
```

- [ ] **Step 2: Start the new bridge**

In one terminal: `python aegis_bridge.py`

Expected stdout:
```
[aegis-bridge] Backend: Ollama
[aegis-bridge] Model:   gemma4:e2b
[aegis-bridge] Ollama:  http://127.0.0.1:11434
[aegis-bridge] Ollama models available: gemma4:e2b, ...
[aegis-bridge] Listening on http://127.0.0.1:7523
[aegis-bridge] Endpoints: POST /classify, GET /health
```

- [ ] **Step 3: Run the smoke test**

In another terminal: `python test_bridge_smoke.py`

Expected: `Bridge health: {'status': 'ok', 'backend': 'ollama', ...}` followed by 8 case results. The header should print "OK" rows; at least 6 of 8 should pass. If <6/8 pass, the model is failing the task — try `--model gemma4:e4b` or a different model before declaring the bridge broken.

If pass: stop the bridge (Ctrl-C) and proceed.

- [ ] **Step 4: Commit**

```bash
git add aegis_bridge.py
git commit -m "Rewrite aegis_bridge.py as a single-call Ollama classifier

- Drop CactusBackend, TransformersBackend, LM Studio summarizer
- Drop POST /summarize endpoint
- POST /classify now takes {text: ...} (renamed from {summary: ...})
- Use Ollama format: <json-schema> for guaranteed valid output
- Single ~200 line module, stdlib only"
```

---

### Task 4: Update middleware router (TDD via Vitest)

**Files:**
- Modify: `middleware/tests/router.test.ts`
- Modify: `middleware/src/router/classify.ts`

- [ ] **Step 1: Update the router test to expect new wire shape**

Edit `middleware/tests/router.test.ts`:

Replace the `startMockBridge` function so it no longer handles `/summarize` and asserts the `/classify` request body has a `text` field:

```typescript
let lastClassifyRequestBody: Record<string, unknown> | null = null;

function startMockBridge(): Promise<number> {
  return new Promise((resolve) => {
    mockServer = http.createServer((req, res) => {
      let body = "";
      req.on("data", (chunk) => { body += chunk; });
      req.on("end", () => {
        res.setHeader("Content-Type", "application/json");

        if (req.url === "/health") {
          res.end(JSON.stringify({ status: "ok", backend: "ollama", model: "gemma4:e2b" }));
        } else if (req.url === "/classify") {
          lastClassifyRequestBody = body ? JSON.parse(body) : null;
          res.end(JSON.stringify(mockClassifyResponse));
        } else {
          res.statusCode = 404;
          res.end(JSON.stringify({ error: "not found" }));
        }
      });
    });

    mockServer.listen(0, "127.0.0.1", () => {
      const addr = mockServer.address();
      if (addr && typeof addr !== "string") resolve(addr.port);
    });
  });
}
```

Then delete the `mockSummarizeResponse` variable and all assignments to it (search the file for `mockSummarizeResponse` and remove). Update each test to drop those lines.

Add one new test asserting the request shape:

```typescript
    it("sends raw text in classify request body", async () => {
      mockClassifyResponse = {
        tool: "classify_safe",
        arguments: { reason: "test" },
        confidence: 0.9,
        time_ms: 10,
      };
      lastClassifyRequestBody = null;

      await classifyFile("hello world", makeConfig(mockPort));
      expect(lastClassifyRequestBody).toEqual({ text: "hello world" });
    });
```

Update the `time_ms` assertion in the first test (`returns safe verdict for classify_safe response`) to use only the classify time (e.g., `expect(result.time_ms).toBe(30);`) since summarize is gone.

Also update the health-check test backend assertion to `"ollama"`:

```typescript
    it("returns ok when bridge is reachable", async () => {
      const health = await healthCheck(makeConfig(mockPort));
      expect(health.status).toBe("ok");
      expect(health.backend).toBe("ollama");
      expect(health.model).toBe("gemma4:e2b");
    });
```

- [ ] **Step 2: Run the tests to verify they fail**

From the repo root:
```bash
cd middleware && npm test -- tests/router.test.ts
```

Expected: failures (because `classifyFile` still calls `/summarize` and sends `{summary}` not `{text}`).

- [ ] **Step 3: Rewrite `middleware/src/router/classify.ts`**

Replace the body of `classifyFile()` to remove the summarize call. The full updated function:

```typescript
export async function classifyFile(
  text: string,
  config: DataGuardConfig
): Promise<ClassifyResult> {
  const bridgeUrl = config.aegisBridgeUrl;
  const timeout = config.aegisBridgeTimeoutMs;

  try {
    const classifyResp = await postJson(
      bridgeUrl,
      "/classify",
      { text },
      timeout
    );

    const toolName = classifyResp.tool as string;
    const args = classifyResp.arguments as Record<string, string> | undefined;
    const confidence = (classifyResp.confidence as number) ?? 0;
    const timeMs = (classifyResp.time_ms as number) ?? 0;

    const verdict = VERDICT_MAP[toolName] ?? "flag_pii";

    return {
      verdict,
      reason: args?.reason ?? args?.types ?? `classified as ${toolName}`,
      confidence,
      pii_types: verdict === "flag_pii" ? (args?.types ?? "email,phone,ssn") : undefined,
      time_ms: timeMs,
    };
  } catch (err) {
    console.error("[aegis-router] Bridge error, falling back to sanitize-everything:", err);
    return {
      verdict: "flag_pii",
      reason: `Bridge unavailable: ${err instanceof Error ? err.message : String(err)}`,
      confidence: 0,
      pii_types: "email,phone,ssn",
      time_ms: 0,
    };
  }
}
```

Also update the file banner JSDoc (lines 1-5) to drop the "summarize + classify" two-step language:

```typescript
// ============================================================================
// AEGIS ROUTER — HTTP client for the Ollama-backed classification bridge
// ============================================================================
// Calls the Python aegis_bridge.py server over localhost to classify file
// content before deciding whether to sanitize, pass through, block, or escalate.
```

And rewrite the JSDoc above `classifyFile`:

```typescript
/**
 * Classify file content via the Aegis bridge.
 *
 * Sends raw text (truncated server-side) to POST /classify on the bridge.
 *
 * On any failure (bridge down, timeout, malformed response) this function
 * degrades gracefully by returning verdict "flag_pii" — causing the caller
 * to fall through to the existing DataGuard sanitize-everything pipeline.
 */
```

- [ ] **Step 4: Run middleware unit tests to verify pass**

```bash
cd middleware && npm test -- tests/router.test.ts
```

Expected: all tests pass (~7-8 tests).

- [ ] **Step 5: Run the full middleware test suite**

```bash
cd middleware && npm test
```

Expected: all non-e2e tests pass. (e2e tests need a real bridge — Task 8.)

- [ ] **Step 6: Commit**

```bash
git add middleware/src/router/classify.ts middleware/tests/router.test.ts
git commit -m "Update middleware router to drop /summarize call

Router now sends raw text to /classify in one hop. Mock bridge and
tests updated to match new wire shape. Health check expects ollama backend."
```

---

### Task 5: Update `backend/api.py`

**Files:**
- Modify: `backend/api.py` (the `analyze_via_bridge` helper, lines 41-93)

- [ ] **Step 1: Replace `analyze_via_bridge()` to drop the summarize hop**

In `backend/api.py`, replace the entire `analyze_via_bridge` function (lines 41-93) with:

```python
async def analyze_via_bridge(text: str) -> dict:
    """
    Run text through the Aegis Bridge: single /classify call.
    Falls back to classify_safe on any network/bridge error so chat is never blocked.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            cls_resp = await client.post(f"{BRIDGE_URL}/classify", json={"text": text})
            cls_resp.raise_for_status()
            cls_data = cls_resp.json()

            tool_name = cls_data.get("tool", "request_permission")
            arguments = cls_data.get("arguments", {})
            confidence = cls_data.get("confidence", 0.0)
            classify_time = cls_data.get("time_ms", 0)

            return {
                "success": True,
                "classification": tool_name,
                "reason": arguments.get("reason", ""),
                "pii_types": arguments.get("types", ""),  # only populated for flag_pii
                "confidence": confidence,
                "summary": "",  # No separate summary stage anymore; field kept for FE compat
                "execution_time_ms": classify_time,
            }
    except httpx.ConnectError:
        return {
            "success": False,
            "classification": "classify_safe",
            "reason": "Bridge unreachable — proceeding without classification",
            "confidence": 0.0,
            "pii_types": "",
            "summary": "",
            "execution_time_ms": 0,
        }
    except Exception as e:
        return {
            "success": False,
            "classification": "classify_safe",
            "reason": f"Bridge error: {str(e)}",
            "confidence": 0.0,
            "pii_types": "",
            "summary": "",
            "execution_time_ms": 0,
        }
```

The `summary` field is kept (as `""`) to avoid breaking the frontend `FileAnalysisResult` interface. Removing it from the frontend is a separate concern.

- [ ] **Step 2: Smoke-test the backend manually**

Start the bridge (terminal 1): `python aegis_bridge.py`
Start the backend (terminal 2): `cd backend && uvicorn api:app --port 8000`
Test the analyze endpoint (terminal 3):

```bash
curl -s -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "John Smith, SSN 123-45-6789, john@example.com", "filename": "test.txt"}'
```

Expected JSON response with `"classification": "flag_pii"` and non-empty `pii_types`.

- [ ] **Step 3: Smoke-test the bridge health proxy**

```bash
curl -s http://127.0.0.1:8000/api/bridge/health
```

Expected: `{"status":"ok","backend":"ollama","model":"gemma4:e2b","bridge_enabled":true}`.

- [ ] **Step 4: Commit**

```bash
git add backend/api.py
git commit -m "Drop /summarize call from backend analyze_via_bridge

Single /classify hop with raw text. Increase timeout to 60s for Ollama.
summary field kept as empty string for frontend interface compat."
```

---

### Task 6: Update `aegis_cli.py`

**Files:**
- Modify: `aegis_cli.py`

- [ ] **Step 1: Find and remove the `step_summarize` function**

The file currently has separate `step_summarize()` (around line 156) and `step_classify()` (around line 185) functions, and `process_file()` calls both. We collapse them into one step.

Read the current `process_file()` function (around lines 318-360) and replace the summarize+classify section with a single classify call. Specifically:

Before (around line 333-342):
```python
    summary, summarize_ms = step_summarize(bridge_url, content)
    ...
    classification, classify_ms = step_classify(bridge_url, summary)
```

After:
```python
    classification, classify_ms = step_classify(bridge_url, content)
```

Update `step_classify` (around line 185) to accept raw content and POST `{"text": content}` to `/classify`. Replace the function body's POST call from:

```python
        resp = bridge_post(bridge_url, "/classify", {"summary": summary})
```

to:

```python
        resp = bridge_post(bridge_url, "/classify", {"text": content[:8000]})
```

And rename the parameter from `summary` to `content` for clarity throughout the function.

Delete the entire `step_summarize` function (it's no longer called).

Update any print statements that mention summarize timing (e.g., `f"Total time: {total_ms:.0f}ms (summarize: ... + classify: ...)"`) to drop the summarize component:

```python
    print(f"  {DIM}Total time: {classify_ms:.0f}ms{RESET}")
```

Update the file's top docstring (lines 5-7) to drop the "Step 2: Summarize" line.

- [ ] **Step 2: Run the CLI against the sample suite**

With the bridge running:

```bash
python aegis_cli.py --all
```

Expected: prints per-file classification with color-coded verdicts. No errors. Total ≤ ~12 files processed.

- [ ] **Step 3: Commit**

```bash
git add aegis_cli.py
git commit -m "Collapse summarize+classify into single /classify call in aegis_cli

Removes step_summarize; step_classify now takes raw file content and
sends it as {text: ...} to the bridge."
```

---

### Task 7: Replace `benchmark.py` with an Ollama-driven version

**Files:**
- Modify: `benchmark.py` (full rewrite — old one depends on `main.py` and Cactus which are being deleted)

- [ ] **Step 1: Replace `benchmark.py`**

Overwrite `benchmark.py` with this Ollama-bridge-driven benchmark:

```python
"""
Aegis Classifier Benchmark — F1 + accuracy across the 4 verdict categories.

Hits the Ollama-backed Aegis bridge at http://127.0.0.1:7523/classify and
scores against a hand-labeled dataset built from samples/.

Usage:
    python benchmark.py
    python benchmark.py --bridge http://127.0.0.1:7523
"""

import argparse
import json
import sys
import time
import urllib.request

# (path, expected_tool) pairs covering all 4 categories
CASES = [
    # classify_safe
    ("samples/open_source_readme.md",      "classify_safe"),
    ("samples/marketing_copy.txt",         "classify_safe"),
    ("samples/blog_post_draft.txt",        "classify_safe"),
    # flag_pii
    ("samples/patient_records.csv",        "flag_pii"),
    ("samples/employee_directory.json",    "flag_pii"),
    ("samples/user_database.json",         "flag_pii"),
    # block_transfer
    ("samples/api_config.env",             "block_transfer"),
    ("samples/kubernetes_secrets.yaml",    "block_transfer"),
    ("samples/docker_compose_prod.yml",    "block_transfer"),
    # request_permission
    ("samples/vendor_evaluation.txt",      "request_permission"),
    ("samples/partnership_agreement.txt",  "request_permission"),
    ("samples/board_meeting_minutes.txt",  "request_permission"),
]


def post_classify(bridge_url, text):
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{bridge_url}/classify",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def f1_for_class(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def main():
    parser = argparse.ArgumentParser(description="Aegis classifier benchmark")
    parser.add_argument("--bridge", default="http://127.0.0.1:7523", help="Bridge URL")
    args = parser.parse_args()

    labels = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]
    # Per-class confusion counts
    tp = {k: 0 for k in labels}
    fp = {k: 0 for k in labels}
    fn = {k: 0 for k in labels}

    rows = []
    total_ms = 0.0

    for path, expected in CASES:
        try:
            with open(path, "r", errors="replace") as f:
                content = f.read()
        except OSError as e:
            print(f"SKIP {path}: {e}")
            continue

        start = time.time()
        try:
            result = post_classify(args.bridge, content)
        except Exception as e:
            print(f"ERROR {path}: {e}")
            continue
        wall_ms = (time.time() - start) * 1000
        total_ms += wall_ms

        predicted = result.get("tool", "request_permission")
        confidence = result.get("confidence", 0.0)
        rows.append((path, expected, predicted, confidence, wall_ms))

        if predicted == expected:
            tp[expected] += 1
        else:
            fp[predicted] = fp.get(predicted, 0) + 1
            fn[expected] = fn.get(expected, 0) + 1

    # Print per-case results
    print()
    print(f"{'file':42s} {'expected':22s} {'predicted':22s} {'conf':>5s} {'ms':>6s}")
    print("-" * 100)
    correct = 0
    for path, expected, predicted, conf, ms in rows:
        mark = "OK" if predicted == expected else "XX"
        if predicted == expected:
            correct += 1
        print(f"{mark} {path:39s} {expected:22s} {predicted:22s} {conf:5.2f} {ms:6.0f}")
    print()

    # Per-class F1
    print(f"{'class':24s} {'P':>6s} {'R':>6s} {'F1':>6s}")
    print("-" * 50)
    macro_f1 = 0.0
    for k in labels:
        p, r, f1 = f1_for_class(tp[k], fp[k], fn[k])
        macro_f1 += f1
        print(f"{k:24s} {p:6.2f} {r:6.2f} {f1:6.2f}")
    macro_f1 /= len(labels)

    total = len(rows)
    acc = correct / total if total else 0.0
    print()
    print(f"Cases:       {total}")
    print(f"Accuracy:    {acc:.2%} ({correct}/{total})")
    print(f"Macro F1:    {macro_f1:.3f}")
    print(f"Avg latency: {total_ms / total if total else 0:.0f} ms")

    sys.exit(0 if acc >= 0.5 else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the benchmark with the bridge running**

```bash
# Terminal 1: ensure bridge is running
python aegis_bridge.py

# Terminal 2:
python benchmark.py
```

Expected: prints per-case rows, per-class P/R/F1, and an overall accuracy + macro F1. This is the baseline for `gemma4:e2b`. Capture the output to share with your teammate.

- [ ] **Step 3: Commit**

```bash
git add benchmark.py
git commit -m "Rewrite benchmark.py to hit the Ollama bridge

Simple urllib-based benchmark across 12 sample files, per-class P/R/F1
plus overall accuracy. Replaces the old Cactus+Gemini hybrid benchmark
which depended on main.py (being deleted)."
```

---

### Task 8: Update `test_e2e.sh`

**Files:**
- Modify: `test_e2e.sh` (lines around 90-110 — the curl smoke tests)

- [ ] **Step 1: Update the curl smoke tests to use `text` field**

In `test_e2e.sh`, find the two `curl -X POST .../classify` invocations and change their JSON bodies from `{"summary": ...}` to `{"text": ...}`.

Before (around line 97):
```bash
  -d '{"summary": "A marketing blog post about new product features. No personal data, no API keys, no credentials."}' \
```

After:
```bash
  -d '{"text": "A marketing blog post about new product features. No personal data, no API keys, no credentials."}' \
```

Same change for the second curl (around line 105) — replace `summary` with `text`.

If `test_e2e.sh` has any reference to `--backend transformers`, `--backend cactus`, or the LM Studio summarizer, drop those flags from the bridge-start command. The bridge no longer accepts them.

- [ ] **Step 2: Run the e2e script**

From the repo root, with Ollama running:

```bash
bash test_e2e.sh
```

Expected: bridge starts, smoke tests print non-empty `tool` field results, TypeScript e2e tests run and pass. Script exits 0.

- [ ] **Step 3: Commit**

```bash
git add test_e2e.sh
git commit -m "Update test_e2e.sh to use new {text} classify body and Ollama backend"
```

---

### Task 9: Delete dead Cactus/FunctionGemma code

**Files:**
- Delete: `model-merge/` (directory)
- Delete: `cactus-compute-research.md`
- Delete: `aegis.py`
- Delete: `main.py`

- [ ] **Step 1: Verify nothing in the kept code still imports the doomed modules**

```bash
grep -rEn "from main import|import main$|from aegis import|import aegis$" \
  --include="*.py" --exclude-dir=__pycache__ --exclude-dir=.venv \
  --exclude-dir=functiongemma-finetuning --exclude-dir=training_files \
  --exclude-dir=model-merge .
```

Expected: empty output. If `benchmark.py` still imports `main`, you missed Step 1 of Task 7 — go fix that first.

```bash
grep -rEn "cactus/python|sys.path.insert.*cactus" \
  --include="*.py" --exclude-dir=__pycache__ --exclude-dir=.venv \
  --exclude-dir=functiongemma-finetuning --exclude-dir=training_files \
  --exclude-dir=model-merge .
```

Expected: empty output (cactus imports should only exist in the to-be-deleted files).

- [ ] **Step 2: Delete the files**

```bash
rm -rf model-merge/
rm cactus-compute-research.md
rm aegis.py
rm main.py
```

- [ ] **Step 3: Run all tests to confirm nothing breaks**

```bash
# Middleware
cd middleware && npm test
cd ..
# Bridge smoke (Ollama + bridge must be running)
python test_bridge_smoke.py
```

Expected: middleware tests all pass; bridge smoke passes at the same rate as before deletion.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "Delete Cactus + FunctionGemma legacy code

- model-merge/ (Cactus conversion + Cactus tests)
- cactus-compute-research.md (sponsor research notes)
- aegis.py (pre-bridge standalone pipeline)
- main.py (Cactus confidence-routing demo)

functiongemma-finetuning/ and training_files/ kept per spec in case
the fine-tune path is ever revisited."
```

---

### Task 10: Update docs and `.mcp.json`

**Files:**
- Modify: `README.md`
- Modify: `INTEGRATION.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `.mcp.json`

- [ ] **Step 1: Fix `.mcp.json` path**

Replace the entire contents of `.mcp.json` with:

```json
{
  "mcpServers": {
    "aegis": {
      "command": "node",
      "args": ["/Users/excallibur/dev/aegis/middleware/dist/mcp-server.js"],
      "cwd": "/Users/excallibur/dev/aegis/middleware"
    }
  }
}
```

(Adjust the path if `$HOME` differs from `/Users/excallibur`. The point is it must point at THIS repo, not `/Users/amaru-mac/...`.)

- [ ] **Step 2: Rewrite the `README.md` Architecture and Quick Start sections**

Open `README.md` and:

1. **Replace the "Architecture" section** (the first ASCII diagram block, roughly lines 5-100): drop the SmolLM2 / LM Studio / Cactus / Transformers backend language. The new architecture text should describe the single Ollama call. Use this replacement:

````markdown
## Architecture

Three components work together:

- **Aegis Bridge** (`aegis_bridge.py`) — Python HTTP server that proxies file content to a local Ollama model (default: `gemma4:e2b`) and returns one of four privacy verdicts as structured JSON.
- **Middleware** (`middleware/`) — TypeScript OpenClaw / MCP plugin. Registers `aegis_read`, `aegis_classify`, and other tools. Routes files through the bridge, then applies DataGuard sanitization for PII files.
- **CLI Test Harness** (`aegis_cli.py`) — Interactive Python script for testing the full pipeline with visible step-by-step output.

## Execution Flow

When an AI agent tries to read a file:

```
AI Agent (Claude, etc.)
  |
  |  calls aegis_read({ path: "samples/patient_records.csv" })
  v
middleware/src/plugin/index.ts (OpenClaw / MCP)
  |
  |  policy check → extract text → POST /classify
  v
aegis_bridge.py (this repo, port 7523)
  |
  |  POST {ollama_url}/api/chat with format: <json-schema>
  v
Ollama running gemma4:e2b (port 11434)
  |
  |  returns {tool, arguments, confidence}
  v
ROUTE on tool:
  classify_safe     → return raw text
  flag_pii          → DataGuard sanitization (regex + placeholders)
  block_transfer    → throw Error, content never returned
  request_permission → return escalation object, ask the human
  bridge unreachable → degrade to flag_pii (sanitize everything)
```
````

2. **Replace the "Quick Start → Prerequisites" section** with:

```markdown
### Prerequisites

- Python 3.12+ with `uv`
- Node.js 18+
- Ollama ≥ 0.5.0 (`brew install ollama` or https://ollama.com/download)
- The `gemma4:e2b` model pulled (`ollama pull gemma4:e2b`)
```

3. **Replace the "1. Start the Bridge" subsection** with:

````markdown
### 1. Start Ollama and the Bridge

```bash
# In one terminal — start Ollama (if not already running as a daemon)
ollama serve

# In another terminal — start the bridge
python aegis_bridge.py
```

Verify:

```bash
curl http://127.0.0.1:7523/health
# {"status":"ok","backend":"ollama","model":"gemma4:e2b","ollama_url":"http://127.0.0.1:11434"}
```
````

4. **Delete the entire "Bridge Options" section** at the bottom of the README (the `--backend cactus`/`--backend transformers`/`--no-lmstudio` block) — those flags are gone. Replace with:

````markdown
## Bridge Options

```bash
# Default — gemma4:e2b on a local Ollama instance
python aegis_bridge.py

# Swap the model
python aegis_bridge.py --model qwen2.5:3b

# Custom Ollama URL (e.g., remote dev box)
python aegis_bridge.py --ollama-url http://192.168.1.10:11434

# Custom bridge port
python aegis_bridge.py --port 8080
```
````

5. **Update the "Project Structure" section**: remove `aegis.py`, `main.py`, `model-merge/`, and `cactus-compute-research.md` references; add `test_bridge_smoke.py`.

- [ ] **Step 3: Update `INTEGRATION.md`**

Open `INTEGRATION.md` and:

1. **Replace the Bridge API Contract section** (the `POST /summarize` and `POST /classify` blocks near the bottom): delete the `POST /summarize` block entirely. Update `POST /classify` to:

````markdown
**`POST /classify`**
```json
// Request
{ "text": "<raw file content>" }

// Response
{
  "tool": "flag_pii",
  "arguments": { "types": "email, phone" },
  "confidence": 0.94,
  "time_ms": 187.2
}
```
````

2. **Update the architecture diagram** at the top (the Frontend ↔ Backend ↔ Bridge ASCII art) to show "POST /classify" directly instead of "POST /summarize, POST /classify".

3. **Update the "Running the Stack" code block** to use Ollama:

````markdown
```bash
# 1. Ollama (if not running)
ollama serve

# 2. Aegis Bridge
python aegis_bridge.py

# 3. Backend
cd backend
pip install -r requirements.txt
uvicorn api:app --port 8000

# 4. Frontend
cd frontend
npm run dev
```
````

4. **Replace the "Bridge Not Available?" section** with a shorter version:

````markdown
## Bridge Not Available?

The bridge needs:
- **Ollama** running locally with `gemma4:e2b` pulled

When the bridge is down the frontend shows a red status dot and all classification gracefully degrades to pass-through.
````

- [ ] **Step 4: Update `AGENTS.md`**

In `AGENTS.md`, replace the **`### Aegis Bridge (aegis_bridge.py)`** subsection (around lines 37-51) with:

````markdown
### Aegis Bridge (`aegis_bridge.py`)

```bash
# Default — gemma4:e2b on local Ollama
python aegis_bridge.py

# Custom model
python aegis_bridge.py --model qwen2.5:3b

# Custom port
python aegis_bridge.py --port 7523
```

The bridge provides `POST /classify` and `GET /health` endpoints on
`http://127.0.0.1:7523`. Requires Ollama ≥ 0.5.0 running locally.
The TypeScript middleware and the Python CLI both call it over localhost.
````

In the same file, find the "Python (root)" section and remove the lines that reference `aegis.py`, `main.py`, `model-merge/`, and Cactus (e.g., delete the `GEMINI_API_KEY=<key> python main.py` and `python aegis.py <file>` example commands).

- [ ] **Step 5: Update `CLAUDE.md`**

In `CLAUDE.md`, find this line near the bottom (under "Prerequisites"):

```
uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter
```

Replace with:

```
ollama serve  # if not already running
python aegis_bridge.py
```

Everything above this (the Aegis tool rules and the NEVER section) stays as-is.

- [ ] **Step 6: Verify all docs are coherent**

```bash
grep -rn "lmstudio\|LM Studio\|SmolLM2\|FunctionGemma\|Cactus\|--backend" \
  README.md INTEGRATION.md AGENTS.md CLAUDE.md .mcp.json
```

Expected: matches only inside historical mentions (e.g., a "Bridge Not Available?" section now rewritten, or kept files like `functiongemma-finetuning/README.md` which isn't in this grep). If you see live references in the four files above, fix them.

- [ ] **Step 7: Commit**

```bash
git add README.md INTEGRATION.md AGENTS.md CLAUDE.md .mcp.json
git commit -m "Update docs and .mcp.json for Ollama migration

- README: rewrite Architecture, Quick Start, Bridge Options
- INTEGRATION: drop /summarize from bridge contract, Ollama in Running the Stack
- AGENTS: simplify bridge commands, drop --backend flag
- CLAUDE: update bridge run command at bottom
- .mcp.json: point at local middleware path"
```

---

### Task 11: Final verification

**Files:** None (verification only)

- [ ] **Step 1: Start the full stack**

```bash
# Terminal 1
ollama serve

# Terminal 2
python aegis_bridge.py

# Terminal 3
cd backend && uvicorn api:app --port 8000

# Terminal 4 (optional)
cd frontend && npm run dev
```

- [ ] **Step 2: Run the four test entry points**

```bash
# 1. Bridge smoke
python test_bridge_smoke.py

# 2. CLI sweep
python aegis_cli.py --all

# 3. Benchmark
python benchmark.py

# 4. End-to-end script
bash test_e2e.sh

# 5. Middleware test suite
cd middleware && npm test
```

Expected: all five pass. Capture the benchmark output (accuracy + macro F1) — that's the baseline for `gemma4:e2b`.

- [ ] **Step 3: Confirm git log on the branch is clean and main is untouched**

```bash
git log --oneline main..ollama-migration
git log --oneline main -3
```

Expected: branch shows the migration commits in order; main shows the pre-migration state (last commit `b9eb4ce category in dictionary fix`).

- [ ] **Step 4: Stop here**

Do NOT push or merge to main. The user will review and coordinate with their teammate before any merge.

---

## Done criteria

- `aegis_bridge.py` is a single-call Ollama classifier, ~200 lines, no Cactus / LM Studio / Transformers code.
- Middleware unit tests + e2e tests pass against the new bridge.
- Backend `/api/analyze` and `/api/chat` work via the new bridge.
- `python test_bridge_smoke.py` exits 0.
- `python benchmark.py` produces an accuracy + macro F1 baseline for `gemma4:e2b`.
- `model-merge/`, `cactus-compute-research.md`, `aegis.py`, `main.py` are deleted.
- `README.md`, `INTEGRATION.md`, `AGENTS.md`, `CLAUDE.md`, `.mcp.json` updated.
- All work lives on the `ollama-migration` branch; `main` is unchanged from the pre-migration commit.
