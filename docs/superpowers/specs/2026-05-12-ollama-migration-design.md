# Ollama Migration Design

**Date:** 2026-05-12
**Status:** Approved
**Author:** Christian Chavez

## Goal

Replace the hackathon-era Cactus + FunctionGemma + LM Studio + SmolLM2 inference stack with a single Ollama call running stock Gemma 4 E2B. Simplifies the bridge from ~530 lines to ~200, removes the need to maintain a fragile fine-tune, and eliminates two external runtime dependencies (Cactus SDK and LM Studio).

## Context

Aegis is a local privacy layer for AI agents. When an agent reads a file through the `aegis_read` MCP tool, the contents are classified on-device into one of four verdicts (`classify_safe`, `flag_pii`, `block_transfer`, `request_permission`) and routed accordingly.

The current implementation has three problems:

1. **The FunctionGemma-270M fine-tune isn't classifying reliably** and would need retraining (Colab GPU, dataset regeneration). The LoRA adapter weights are gitignored and not present locally.
2. **Cactus is dead code on this machine.** The Cactus SDK requires built C++ artifacts under `cactus/python/src` plus converted GGUF weights — neither exists locally. Cactus was a hackathon sponsor; without that constraint, it offers no value on a developer workstation.
3. **The summarizer (SmolLM2 via LM Studio) is an unnecessary second hop.** A 3B-class model can read 8K of file text and classify directly in one call.

This design replaces the entire inference layer with Ollama running `gemma4:e2b` (Gemma 4 Effective 2B — ~1.5GB at 4-bit, 128K context, fast enough on Apple Silicon).

## Non-goals

- Mobile deployment. Aegis remains a dev-machine MCP server. If mobile becomes a target later, Cactus may come back — but as a *new* surface, not the current one.
- Changing the MCP tool contracts (`aegis_read`, `aegis_classify`, etc.).
- Changing the four-verdict semantics or the DataGuard sanitization pipeline downstream of classification.
- Rewriting the demo frontend/backend chat UI beyond the minimum needed to drop the `/summarize` call.

## Architecture

### Before

```
File text
  ├─► POST /summarize → SmolLM2 1.7B via LM Studio  (port 1234)
  └─► POST /classify  → FunctionGemma-270M via Cactus OR Transformers
                         → {tool, arguments, confidence, time_ms}
```

### After

```
File text (truncated to 8K chars)
  └─► POST /classify → Gemma 4 E2B via Ollama        (port 11434)
                        → {tool, arguments, confidence, time_ms}
```

The wire-level response shape from `/classify` is **identical** to the previous bridge contract. Everything downstream (middleware router, backend `analyze_via_bridge`, frontend file-analysis card, `aegis_read` routing on the verdict) stays unchanged.

## Components

### `aegis_bridge.py` (rewrite, ~200 lines)

**Removed:**
- `CactusBackend` class
- `TransformersBackend` class
- `_summarize_via_lmstudio` and all SmolLM2 / LM Studio code
- `parse_tool_call` string parser for the `call:tool_name{key: <escape>value<escape>}` format
- CLI flags: `--backend`, `--summarizer`, `--lmstudio-url`, `--lmstudio-model`, `--no-lmstudio`

**Added:**
- `OllamaBackend` class with a single `classify(text)` method
- One `POST {ollama_url}/api/chat` call per request with `format: <json-schema>` for structured output
- Startup probe of `GET {ollama_url}/api/tags` to verify the model is pulled; print a clear `ollama pull gemma4:e2b` hint if missing (warn, do not fail)

**Endpoints:**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/classify` | Accepts `{text: string}`. Server truncates to 8K chars. Returns the classification result. |
| `GET` | `/health` | Returns `{status, backend: "ollama", model: <id>, ollama_url}`. |
| `POST` | `/summarize` | **Removed.** All callers updated. |

**CLI flags:**

```bash
python aegis_bridge.py \
  --model gemma4:e2b \
  --ollama-url http://127.0.0.1:11434 \
  --host 127.0.0.1 \
  --port 7523
```

### Classification schema

We use Ollama's `format` parameter with a JSON schema instead of relying on regex parsing of free-text tool calls. Every successful response is guaranteed to be valid JSON matching this shape:

```json
{
  "type": "object",
  "properties": {
    "tool": {
      "type": "string",
      "enum": ["classify_safe", "flag_pii", "block_transfer", "request_permission"]
    },
    "arguments": {
      "type": "object",
      "properties": {
        "reason": { "type": "string" },
        "types":  { "type": "string" }
      }
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    }
  },
  "required": ["tool", "arguments", "confidence"]
}
```

**System prompt** teaches the four verdicts inline (same definitions as the old `PRIVACY_TOOLS` block, restated in plain prose). The model is instructed to:

- Pick exactly one of the four tools
- Fill `arguments.types` (comma-separated PII types) when calling `flag_pii`, otherwise `arguments.reason`
- Self-rate `confidence` in [0, 1] — used downstream for routing decisions (e.g., low-confidence `flag_pii` could escalate)

If Ollama returns a response that fails schema validation (shouldn't happen with `format` enforcement, but defensively), the bridge returns `{tool: "request_permission", arguments: {reason: "Bridge could not parse response"}, confidence: 0.0, time_ms}`. This is the existing safe-default behavior.

### Middleware (`middleware/src/router/classify.ts`)

Currently calls `POST /summarize` first, then `POST /classify` with the summary. Simplified to a single `POST /classify` with raw extracted text.

Other middleware files (`tools/dataguard_read.ts`, `tools/aegis_classify.ts`, the sanitize pipeline, the hooks) are **untouched** — they only depend on the verdict, not on how it was produced.

### Backend (`backend/api.py`)

The `analyze_via_bridge()` async helper currently:

```python
# Old:
summary = await POST /summarize { text }
result  = await POST /classify  { summary }
```

becomes:

```python
# New:
result = await POST /classify { text }
```

Same return shape. `bridge_enabled` toggle, fallback-to-`classify_safe` on `ConnectError`, and the chat / file-analysis routes are all unchanged.

## File-level cleanup

### Delete

- `model-merge/` (entire directory — Cactus conversion + Cactus tests)
- `cactus-compute-research.md`
- `aegis.py` (standalone pre-bridge pipeline; superseded by the bridge)
- `main.py` (Cactus confidence-routing demo)

### Adapt to Ollama

- `benchmark.py` — repoint to `POST /classify` on the bridge. Keeps F1 scoring honest against the new model. (Adapt rather than delete because we want to measure whether `gemma4:e2b` is good enough.)
- `aegis_cli.py` — should work as-is since the bridge contract is preserved; smoke-test only.
- `test_e2e.sh` — smoke-test against the new bridge.

### Keep untouched

- `functiongemma-finetuning/` — preserved in case we revisit fine-tuning (per user instruction)
- `training_files/` — preserved (per user instruction)
- `functiongemma-research.md` — historical reference

### Docs to update

- `README.md` — rewrite Architecture, Quick Start, Project Structure, Bridge Options. Remove all Cactus/LM Studio/SmolLM2 references.
- `INTEGRATION.md` — drop `/summarize` from the bridge API contract section; update bridge run commands.
- `AGENTS.md` — drop `--backend` flag references; update bridge commands.
- `CLAUDE.md` — keep the Aegis MCP tool rules at top; update the bridge run command at the bottom.
- `.mcp.json` — fix the `/Users/amaru-mac/...` path to the local `middleware` build path (`/Users/excallibur/dev/aegis/middleware/dist/mcp-server.js`).

## Error handling

Inherits the existing layered strategy from `AGENTS.md`:

- **Ollama unreachable / classify times out** — bridge returns 500; middleware `router/classify.ts` catches and degrades to `flag_pii` (sanitize-all). This is the same "bridge down → fail closed" behavior we have today.
- **Schema-invalid JSON from Ollama** — shouldn't happen with `format` enforcement; defensively return `request_permission` with confidence 0.0.
- **Empty `text` field** — bridge returns 400 (existing behavior).
- **Model not pulled** — startup probe prints a clear hint; runtime requests will hit Ollama's own 404 and surface as 500 from the bridge.

## Testing

### Smoke tests (manual, post-implementation)

1. `ollama pull gemma4:e2b && ollama serve` (if not already running)
2. `python aegis_bridge.py` → expect "Listening on http://127.0.0.1:7523"
3. `curl http://127.0.0.1:7523/health` → expect Ollama backend, gemma4:e2b model
4. `python aegis_cli.py samples/patient_records.csv` → expect `flag_pii`
5. `python aegis_cli.py samples/api_config.env` → expect `block_transfer`
6. `python aegis_cli.py samples/open_source_readme.md` → expect `classify_safe`
7. `python aegis_cli.py samples/vendor_evaluation.txt` → expect `request_permission`

### Automated

- `python benchmark.py` after the adaptation — F1 across all four categories. First run establishes the baseline for `gemma4:e2b`; we'll judge whether to swap models from the actual numbers, not a pre-set bar.
- `cd middleware && npm test` — unit tests for `router/classify.ts` updated to match new request shape.
- `npx vitest run tests/e2e.test.ts` — end-to-end through the bridge (requires Ollama running).
- `bash test_e2e.sh` — repo-level smoke.

## Risks & open questions

- **Gemma 4 E2B classification quality on this 4-way task is unmeasured.** The benchmark adaptation is the first thing to run after the bridge swap — if E2B underperforms, the design accommodates swapping `--model` to `gemma4:e4b`, `qwen2.5:3b`, etc. with no code changes.
- **Ollama must be running before the bridge starts.** Today's setup has the same requirement for LM Studio + the classifier process. Net dependency count drops from 2 → 1.
- **JSON schema mode in Ollama requires a recent version** (≥0.5.0 for `format: <schema>`; older versions only support `format: "json"`). The bridge should check the Ollama version on startup and warn if too old.

## Rollback plan

The previous bridge code lives in git history. If Gemma 4 E2B turns out to be inadequate and we want FunctionGemma back, `git revert` the bridge rewrite. The middleware/backend changes (`/summarize` removal) would need a separate revert. Total rollback footprint: 3-5 commits.
