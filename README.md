# Aegis

A local privacy layer for agentic AI. Aegis intercepts file access from AI agents, classifies sensitivity on-device using fine-tuned FunctionGemma, and routes to the appropriate action: passthrough, sanitize, block, or escalate for human review.

## Architecture

Three components work together:

- **Aegis Bridge** (`aegis_bridge.py`) — Python HTTP server wrapping two on-device models: SmolLM2 for summarization and FunctionGemma-270M for classification. Dual backend support (Cactus SDK or HuggingFace Transformers).
- **Middleware** (`middleware/`) — TypeScript OpenClaw plugin. Registers `aegis_read`, `aegis_classify`, and other tools. Routes files through the bridge, then applies DataGuard sanitization for PII files.
- **CLI Test Harness** (`aegis_cli.py`) — Interactive Python script for testing the full pipeline with visible step-by-step output.

## Execution Flow

When an AI agent tries to read a file, the full pipeline executes:

```
AI Agent (Claude, etc.)
  |
  |  calls aegis_read({ path: "samples/patient_records.csv" })
  |
  v
+-------------------------------------------------------------+
|  plugin/index.ts                          [OpenClaw plugin]  |
|  Registers tools + hooks at startup                          |
|  -----------------------------------------------------------+
|  also registers: before_tool_call hook                       |
|  (blocks native Read/Glob/cat -- forces agent to use aegis)  |
+----------------------------+--------------------------------+
                             |
                             v
+-------------------------------------------------------------+
|  tools/dataguard_read.ts                    [aegis_read]     |
|                                                              |
|  Step 1: checkPath()           <-- sanitize/policy.ts        |
|          Deny globs (.env, .ssh, .pem)?                      |
|          Under allowed roots?                                |
|                                                              |
|  Step 2: checkFileSize()       <-- sanitize/policy.ts        |
|          Under 5MB limit?                                    |
|                                                              |
|  Step 3: extractText()         <-- sanitize/extract.ts       |
|          PDF -> pdftotext/pdf-parse                          |
|          DOCX -> mammoth                                     |
|          Everything else -> UTF-8 read                       |
|                                                              |
|  Step 0: classifyFile(text)    <-- router/classify.ts        |
|          +------------------------------+                    |
|          | POST /summarize (8000 chars)  |                    |
|          |         |                     |                    |
|          |         v                     |                    |
|          |  aegis_bridge.py ------------ | ---- Python ----  |
|          |  |                            |                    |
|          |  |  SmolLM2 (LM Studio)       |                    |
|          |  |  "File contains SSNs,      |                    |
|          |  |   emails, phone numbers"   |                    |
|          |  |         |                  |                    |
|          |  v         v                  |                    |
|          | POST /classify (summary)      |                    |
|          |  |                            |                    |
|          |  |  FunctionGemma-270M        |                    |
|          |  |  call:flag_pii{            |                    |
|          |  |    types: "email,ssn"}     |                    |
|          |  |         |                  |                    |
|          |  v         v                  |                    |
|          |  { verdict: "flag_pii" }      |                    |
|          +------------------------------+                    |
|                    |                                         |
|                    v                                         |
|  +--- ROUTE on verdict -----------------------------------+  |
|  |                                                        |  |
|  |  safe -------> Return raw text, 0 redactions           |  |
|  |                method: "aegis-safe"                     |  |
|  |                (NO sanitization, NO cache, NO LLM)      |  |
|  |                                                        |  |
|  |  flag_pii --> DataGuard sanitization pipeline           |  |
|  |                |                                       |  |
|  |                +-- Cache check                         |  |
|  |                +-- detect() [regex+entropy]            |  |
|  |                +-- applyRedactions() [placeholders]    |  |
|  |                +-- vault (store originals)             |  |
|  |                +-- LLM refinement (Ollama/OpenRouter)  |  |
|  |                +-- Cache write                         |  |
|  |                +-- Return sanitized text               |  |
|  |                   method: "llm+regex" / "regex-only"   |  |
|  |                                                        |  |
|  |  block ------> THROW Error("Aegis blocked file")       |  |
|  |                Content NEVER returned to agent          |  |
|  |                                                        |  |
|  |  escalate ---> Return { content: null,                 |  |
|  |                  escalation: {                         |  |
|  |                    message: "Ask user for              |  |
|  |                    permission before proceeding"       |  |
|  |                }}                                      |  |
|  |                method: "aegis-escalate"                 |  |
|  +--------------------------------------------------------+  |
|                                                              |
|  Bridge DOWN? --> Degrade to flag_pii (sanitize all)         |
+--------------------------------------------------------------+
```

### The Four Verdicts

| Verdict | FunctionGemma Tool | What Happens | Content Returned? |
|---|---|---|---|
| **safe** | `classify_safe` | Passthrough, no sanitization | Yes, raw text |
| **flag_pii** | `flag_pii` | Full DataGuard pipeline (regex + LLM + cache) | Yes, sanitized with placeholders |
| **block** | `block_transfer` | Throw error, deny access | No |
| **escalate** | `request_permission` | Return escalation object, ask human | No (`content: null`) |
| **bridge down** | *(none)* | Degrade to `flag_pii`, sanitize everything | Yes, sanitized |

**SAFE** (`open_source_readme.md`): FunctionGemma says "no sensitive data" -- raw file returned directly to agent. Zero overhead beyond classification. No regex, no LLM, no cache.

**FLAG_PII** (`patient_records.csv`): FunctionGemma says "contains PII" -- full DataGuard pipeline runs. Regex detects SSNs/emails/phones, replaces with `__SSN_1__`, `__EMAIL_1__` placeholders, optionally LLM refines, cached, sanitized text returned to agent with redaction count.

**BLOCK** (`api_config.env`): FunctionGemma says "contains secrets" -- throws an Error. Agent gets an error message, never sees any file content. Two layers: path-based blocking (`.env` glob) AND content-based blocking (FunctionGemma classification).

**ESCALATE** (`vendor_evaluation.txt`): FunctionGemma says "ambiguous, needs human" -- returns `content: null` with a structured escalation message telling the agent to ask the user for permission before proceeding.

**BRIDGE DOWN**: Graceful degradation -- treats every file as `flag_pii`, sanitize-everything mode (same as before Aegis existed). Never crashes.

## Quick Start

### Prerequisites

- Python 3.12+ with `uv`
- Node.js 18+
- LM Studio running with `smollm2-1.7b-instruct` loaded (port 1234)
- The `aegis-adapter` model directory (FunctionGemma-270M fine-tuned weights)

### 1. Start the Bridge

```bash
uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter
```

The bridge auto-detects LM Studio for summarization. Verify with:

```bash
curl http://127.0.0.1:7523/health
# {"status":"ok","backend":"transformers","model":"./aegis-adapter","summarizer":"SmolLM2 via LM Studio (http://127.0.0.1:1234)"}
```

### 2. Run the CLI Test Harness

```bash
# All sample files
python aegis_cli.py --all

# Single file
python aegis_cli.py samples/patient_records.csv

# Classification only (no action execution)
python aegis_cli.py --classify-only samples/api_config.env
```

### 3. Run the Middleware Tests

```bash
cd middleware
npm install
npm test                              # unit tests (no bridge needed)
npx vitest run tests/e2e.test.ts      # e2e tests (bridge must be running)
```

## Project Structure

```
aegis_bridge.py          Python HTTP bridge (FunctionGemma + SmolLM2)
aegis_cli.py             CLI test harness
aegis.py                 Original standalone privacy pipeline
main.py                  Hybrid routing engine (Cactus confidence-based)
benchmark.py             30-case benchmark with F1 scoring
samples/                 12 synthetic test files (all 4 categories)

middleware/
  src/
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
# Transformers backend (default, any HuggingFace model)
uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter

# Cactus backend (requires converted GGUF weights)
uv run python aegis_bridge.py --backend cactus

# Custom port
uv run python aegis_bridge.py --port 8080

# Disable LM Studio summarizer (use truncated text)
uv run python aegis_bridge.py --backend transformers --no-lmstudio
```
