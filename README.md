# Aegis

A local privacy layer for agentic AI. Aegis intercepts file access from AI agents, classifies sensitivity on-device using an in-process embedding model + trained LR head, and routes to the appropriate action: passthrough, sanitize, block, or escalate for human review.

## Architecture

Three components work together:

- **Aegis Bridge** (`aegis_bridge.py`) — Python HTTP server that classifies file content using an in-process `google/embeddinggemma-300m` embedding model + trained LR head (default: `--backend local`) and returns one of four privacy verdicts as structured JSON. An Ollama backend (`--backend ollama`) remains available for dev / A/B comparison.
- **Middleware** (`middleware/`) — TypeScript OpenClaw / MCP plugin. Registers `aegis_read`, `aegis_classify`, and other tools. Routes files through the bridge, then applies DataGuard sanitization for PII files.

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
  |  embeddinggemma-300m (in-process) → LR head (aegis-head/lr.joblib)
  |  returns {tool, arguments, confidence}  [p50 ~78 ms]
  v
ROUTE on tool:
  classify_safe     → return raw text
  flag_pii          → DataGuard sanitization (regex + placeholders)
  block_transfer    → throw Error, content never returned
  request_permission → return escalation object, ask the human
  bridge unreachable → degrade to flag_pii (sanitize everything)
```

### The Four Verdicts

| Verdict | Classifier Label | What Happens | Content Returned? |
|---|---|---|---|
| **safe** | `classify_safe` | Passthrough, no sanitization | Yes, raw text |
| **flag_pii** | `flag_pii` | Full DataGuard pipeline (regex + LLM + cache) | Yes, sanitized with placeholders |
| **block** | `block_transfer` | Throw error, deny access | No |
| **escalate** | `request_permission` | Return escalation object, ask human | No (`content: null`) |
| **bridge down** | *(none)* | Degrade to `flag_pii`, sanitize everything | Yes, sanitized |

**SAFE** (`open_source_readme.md`): Classifier says "no sensitive data" — raw file returned directly to agent. Zero overhead beyond classification. No regex, no LLM, no cache.

**FLAG_PII** (`patient_records.csv`): Classifier says "contains PII" — full DataGuard pipeline runs. Regex detects SSNs/emails/phones, replaces with `__SSN_1__`, `__EMAIL_1__` placeholders, optionally LLM refines, cached, sanitized text returned to agent with redaction count.

**BLOCK** (`api_config.env`): Classifier says "contains secrets" — throws an Error. Agent gets an error message, never sees any file content. Two layers: path-based blocking (`.env` glob) AND content-based blocking (classifier verdict).

**ESCALATE** (`vendor_evaluation.txt`): Classifier says "ambiguous, needs human" — returns `content: null` with a structured escalation message telling the agent to ask the user for permission before proceeding.

**BRIDGE DOWN**: Graceful degradation -- treats every file as `flag_pii`, sanitize-everything mode (same as before Aegis existed). Never crashes.

## Quick Start

### Prerequisites

- Python 3.12+ with `uv`
- Node.js 18+
- A Hugging Face account with a READ token (for the first-run model download)

### 1. Install dependencies and authenticate

```bash
uv sync

# One-time HF auth — needed to download embeddinggemma-300m (~600 MB)
hf auth login   # or: huggingface-cli login
```

The first time the bridge starts it downloads `google/embeddinggemma-300m` into `~/.cache/huggingface/`. Subsequent runs load from cache in ~1–2 s.

### 2. Start the Bridge

```bash
python aegis_bridge.py
```

Verify:

```bash
curl http://127.0.0.1:7523/health
# {"status":"ok","backend":"local","model":"google/embeddinggemma-300m","head":"aegis-head/lr.joblib"}
```

Classifier accuracy: **94.90%** on the 98-sample held-out eval set (Wilson 95% CI [88.6%, 97.8%]).
See [`docs/eval-results/scorecard.md`](docs/eval-results/scorecard.md) for full results.

> **Optional Ollama backend** — `--backend ollama` still works for dev / A/B comparison.
> Requires `ollama serve` running with `gemma4:31b` pulled.

### 3. Connect an Agent via MCP

The middleware runs as an MCP server. Any MCP-compatible agent can use Aegis tools.

```bash
cd middleware
npm install
npm run build
```

**Claude Code** — add to your project's `.claude/settings.json`:

```json
{
  "mcpServers": {
    "aegis": {
      "command": "node",
      "args": ["/Users/amaru-mac/Documents/hackathons/deepmind-cactus/middleware/dist/mcp-server.js"],
      "cwd": "/Users/amaru-mac/Documents/hackathons/deepmind-cactus/middleware"
    }
  }
}
```

**Claude Desktop** — add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aegis": {
      "command": "node",
      "args": ["/Users/amaru-mac/Documents/hackathons/deepmind-cactus/middleware/dist/mcp-server.js"],
      "cwd": "/Users/amaru-mac/Documents/hackathons/deepmind-cactus/middleware"
    }
  }
}
```

Once connected, the agent has 4 tools:

| Tool | Description |
|------|-------------|
| `aegis_read` | Read a file through the privacy router (classify + sanitize/block/escalate) |
| `aegis_classify` | Classify a file's sensitivity without reading its content |
| `aegis_sanitize_path` | Force re-sanitization of a file (bypasses cache) |
| `aegis_policy_explain` | Show current security policy and session stats |

### 4. Run the Middleware Tests

```bash
cd middleware
npm test                              # unit tests (no bridge needed)
npx vitest run tests/e2e.test.ts      # e2e tests (bridge must be running)
```

## Project Structure

```
aegis_bridge.py          Python HTTP bridge (local embeddinggemma-300m + LR head)
aegis-head/lr.joblib     Trained LR classification head
eval.py                  98-sample held-out eval (Phase 3b)
eval_fresh.py            107-sample fresh held-out (Phase 3b.5)
eval_regression.py       10-case ambiguity regression suite
samples/                 Held-out eval corpus (4 verdict classes)
train/                   curated_data, prompt_sweep, train_head, eval_head
tools/                   sample_collector.py (Channel C GitHub mining)
docs/eval-results/       Held-out eval scorecards (scorecard.md)

middleware/
  src/
    mcp-server.ts        MCP server entry point (agent integration)
    plugin/index.ts      OpenClaw plugin entry point
    router/classify.ts   HTTP client for the bridge
    tools/
      dataguard_read.ts  aegis_read tool (main pipeline)
      aegis_classify.ts  Standalone classification tool
      dataguard_search.ts, dataguard_patch_file.ts, ...
    hooks/
      before_tool_call.ts  Intercepts native file reads
    sanitize/
      detector.ts        Regex + entropy PII detection
      sanitize.ts        Two-pass sanitization (regex + LLM)
      policy.ts          Path/size policy enforcement
      extract.ts         Text extraction (PDF, DOCX, text)
      vault.ts           In-memory original<->placeholder store
      cache.ts           File-based sanitization cache
      audit.ts           JSONL audit logging
    types.ts             Central type registry
  tests/
    detector.test.ts     PII detector unit tests
    router.test.ts       Router client unit tests (mock HTTP)
    e2e.test.ts          Full pipeline e2e tests (requires bridge)
```

## Bridge Options

```bash
# Default — in-process embeddinggemma-300m + LR head (no Ollama required)
python aegis_bridge.py

# Ollama backend — for dev / A/B comparison (requires ollama serve + gemma4:31b)
python aegis_bridge.py --backend ollama

# Custom Ollama URL (e.g., remote dev box) — only applies with --backend ollama
python aegis_bridge.py --backend ollama --ollama-url http://192.168.1.10:11434

# Custom bridge port
python aegis_bridge.py --port 8080
```
