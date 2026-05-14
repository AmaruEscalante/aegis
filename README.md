# Aegis

A local privacy layer for agentic AI. Aegis intercepts file access from AI agents, classifies sensitivity on-device using a local Ollama model, and routes to the appropriate action: passthrough, sanitize, block, or escalate for human review.

## Architecture

Three components work together:

- **Aegis Bridge** (`aegis_bridge.py`) — Python HTTP server that proxies file content to a local Ollama model (default: `gemma4:31b`) and returns one of four privacy verdicts as structured JSON.
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
Ollama running gemma4:31b (port 11434)
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

### The Four Verdicts

| Verdict | Ollama Tool Call | What Happens | Content Returned? |
|---|---|---|---|
| **safe** | `classify_safe` | Passthrough, no sanitization | Yes, raw text |
| **flag_pii** | `flag_pii` | Full DataGuard pipeline (regex + LLM + cache) | Yes, sanitized with placeholders |
| **block** | `block_transfer` | Throw error, deny access | No |
| **escalate** | `request_permission` | Return escalation object, ask human | No (`content: null`) |
| **bridge down** | *(none)* | Degrade to `flag_pii`, sanitize everything | Yes, sanitized |

**SAFE** (`open_source_readme.md`): Ollama says "no sensitive data" — raw file returned directly to agent. Zero overhead beyond classification. No regex, no LLM, no cache.

**FLAG_PII** (`patient_records.csv`): Ollama says "contains PII" — full DataGuard pipeline runs. Regex detects SSNs/emails/phones, replaces with `__SSN_1__`, `__EMAIL_1__` placeholders, optionally LLM refines, cached, sanitized text returned to agent with redaction count.

**BLOCK** (`api_config.env`): Ollama says "contains secrets" — throws an Error. Agent gets an error message, never sees any file content. Two layers: path-based blocking (`.env` glob) AND content-based blocking (Ollama classification).

**ESCALATE** (`vendor_evaluation.txt`): Ollama says "ambiguous, needs human" — returns `content: null` with a structured escalation message telling the agent to ask the user for permission before proceeding.

**BRIDGE DOWN**: Graceful degradation -- treats every file as `flag_pii`, sanitize-everything mode (same as before Aegis existed). Never crashes.

## Quick Start

### Prerequisites

- Python 3.12+ with `uv`
- Node.js 18+
- Ollama ≥ 0.5.0 (`brew install ollama` or https://ollama.com/download)
- The `gemma4:31b` model pulled (`ollama pull gemma4:31b`)

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
# {"status":"ok","backend":"ollama","model":"gemma4:31b","ollama_url":"http://127.0.0.1:11434"}
```

### 2. Connect an Agent via MCP

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

### 3. Run the CLI Test Harness (no agent needed)

```bash
# All sample files
python aegis_cli.py --all

# Single file
python aegis_cli.py samples/patient_records.csv

# Classification only (no action execution)
python aegis_cli.py --classify-only samples/api_config.env
```

### 4. Run the Middleware Tests

```bash
cd middleware
npm test                              # unit tests (no bridge needed)
npx vitest run tests/e2e.test.ts      # e2e tests (bridge must be running)
```

## Project Structure

```
aegis_bridge.py          Python HTTP bridge (Ollama-backed, gemma4:31b)
aegis_cli.py             CLI test harness
benchmark.py             30-case benchmark with F1 scoring
test_bridge_smoke.py     Smoke test for the bridge / Ollama integration
samples/                 12 synthetic test files (all 4 categories)

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
# Default — gemma4:31b on a local Ollama instance
python aegis_bridge.py

# Swap the model
python aegis_bridge.py --model qwen2.5:3b

# Custom Ollama URL (e.g., remote dev box)
python aegis_bridge.py --ollama-url http://192.168.1.10:11434

# Custom bridge port
python aegis_bridge.py --port 8080
```
