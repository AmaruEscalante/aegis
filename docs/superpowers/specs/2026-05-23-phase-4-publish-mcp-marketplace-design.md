# Phase 4 — Publish as MCP Marketplace Plugin (Design Spec)

**Date:** 2026-05-23
**Phase:** 4 (of the [Aegis roadmap](../../roadmap.md))
**Status:** Approved — ready to plan
**Predecessor:** Phase 3b (shipped head at 94.90% / 78 ms warm p50, merged in PR #3) + Phase 3b.5 (failed gate, rolled back, docs preserved) + cleanup branch (`bee65a2`, removed hackathon residue)
**Successor:** Phase 4.1 (cross-platform CI, post-launch refinements) or Phase 5 (image / OCR support)

## Goal

Publish Aegis as a one-command-install MCP plugin so a privacy-conscious developer can go from "I want this" to "it's protecting me" in under 2 minutes. Ship to npm, the Anthropic MCP directory, and the Claude Code plugin marketplace.

The shipped accuracy is the Phase 3b head (94.90% on the 98-sample held-out, one documented fail-open case). The improvements catalogued in [`docs/limits-and-improvements.md`](../../limits-and-improvements.md) stay parked — Phase 4 is about distribution and UX, not accuracy.

## Success criteria

v1.0.0 ships when all 9 conditions hold:

1. **`npx aegis-mcp` works end-to-end** from a fresh machine (Python 3.12+ present, no `~/.aegis-mcp/` cache, no existing Claude Code config) within 2 minutes including embedding-model download.
2. **One consent prompt fires** on first run and is recorded in `~/.aegis-mcp/install.log`.
3. **Hook is correctly added** to `~/.claude/settings.json` on consent; correctly removed on `/aegis-uninstall`. Backup of pre-install settings.json kept at `~/.aegis-mcp/backups/`.
4. **All 5 slash commands respond** with sensible output: `/aegis-status`, `/aegis-policy`, `/aegis-enable-hook`, `/aegis-disable-hook`, `/aegis-uninstall`.
5. **PDF + DOCX classification works** for 12 fixture files (3 per verdict class); image files (`.jpg`, `.png`, `.gif`, `.webp`, `.heic`) return `request_permission` without attempting OCR.
6. **Demo GIF embedded in README** at ≤ 5 MB, showing install → safe file → credentials file → PII file → `/aegis-status`.
7. **npm package size ≤ 1 MB compressed** (excludes the 150 MB embedding model, which is HF Hub-cached on first run).
8. **MIT `LICENSE` at repo root.**
9. **Submitted to all 3 channels**: npm publish completed, Anthropic MCP directory PR opened, Claude Code plugin marketplace submission filed.

## Decisions locked from brainstorming

| Decision | Choice | Rationale |
|---|---|---|
| Plugin name | `aegis-mcp` | Explicit about being an MCP plugin; easier marketplace search |
| License | MIT | Max adoption; standard for hobby-to-production OSS plugins |
| Telemetry | Off, no opt-in | Cleanest privacy story; matches the on-device positioning |
| Install command | `npx aegis-mcp` (TS spawns Python bridge) | Single-command UX; matches MCP server conventions |
| Python venv strategy | User-cached at `~/.aegis-mcp/venv/` | Cross-platform; first-run installs, subsequent runs reuse |
| Bridge port | Ephemeral (TS picks free port at startup, passes via `--port`) | No conflicts with other Aegis instances or services |
| Bridge lifecycle | TS server owns subprocess (start on MCP boot, kill on shutdown) | Clean and contained; no system-service install needed |
| Enforcement mode | Mode 2-seamless: hook installed with single Y/n consent on first run | Strong guarantee + user trust via one-second consent moment |
| Image classification | `request_permission` verdict (no OCR in v1) | Fail-safe; zero engineering; honest about capability |
| Distribution channels | npm + Anthropic MCP directory + Claude Code marketplace | Maximum reach for one publish step |
| Privacy framing | Hero promise + reproducibility receipts (separate `docs/PRIVACY.md`) | Differentiator vs cloud alternatives; trust through verifiability |
| Packaging layout | Move `aegis_bridge.py` → `aegis/bridge.py`, `aegis-head/` → `aegis/head/` | Cleaner npm `"files"` allowlist; standard Python package shape |

## Architecture

```
                       User runs: npx aegis-mcp
                                  │
                                  ▼
                     ┌─────────────────────────────┐
                     │  middleware/dist/cli.js     │  (Wave 1)
                     │  ─ Parse argv               │
                     │  ─ Show consent prompt      │
                     │  ─ Backup settings.json     │
                     │  ─ Install hook (on Y)      │
                     │  ─ Install skill            │
                     │  ─ Start bridge_launcher    │
                     └────────────┬────────────────┘
                                  │
              ┌───────────────────┼────────────────────┐
              │                   │                    │
              ▼                   ▼                    ▼
   ┌─────────────────┐   ┌──────────────────┐   ┌───────────────────┐
   │ bridge_launcher │   │ skills/aegis/    │   │ ~/.claude/        │
   │ ─ Detect Python │   │ ─ SKILL.md       │   │   settings.json   │
   │ ─ pip install   │   │ ─ commands/*.md  │   │ ─ hook entry      │
   │ ─ Spawn bridge  │   │ ─ scripts/*.js   │   │   added (namespaced
   │ ─ Healthcheck   │   └──────────────────┘   │   "aegis-mcp:...") │
   │ ─ Stdio bridge  │                          └───────────────────┘
   │   to MCP        │
   └────────┬────────┘
            │ spawns
            ▼
   ┌─────────────────┐
   │ aegis/bridge.py │  (Python HTTP server on ephemeral port)
   │                 │
   │  ┌──────────────┴─────────┐
   │  │ Embedder (sentence-    │
   │  │   transformers loading │
   │  │   embeddinggemma-300m  │
   │  │   from HF Hub cache)   │
   │  └────────────────────────┘
   │                 │
   │  ┌──────────────┴─────────┐
   │  │ aegis/head/lr.joblib   │
   │  │   (LR head, 4 verdicts)│
   │  └────────────────────────┘
   └─────────────────┘
```

When Claude tries to read a file:

```
Claude → Read(path)
            │
            ▼ (hook intercepts)
       hook-enforce.js → reject: "use aegis_read instead"
            │
            ▼
       Claude retries with: aegis_read(path)
            │
            ▼
       MCP server in middleware/dist/
            ├─ extract text (utf-8 / pdf-parse / mammoth / image → request_permission)
            └─ POST /classify to bridge → verdict → route
                ├─ classify_safe → return content
                ├─ flag_pii → sanitize and return
                ├─ block_transfer → throw, content never returned
                └─ request_permission → escalate to user
```

## Components

### `middleware/src/cli.ts` (NEW)

Entry point invoked by `npx aegis-mcp`. Subcommands:
- (default, no args) → install flow + start MCP server
- `install-hook` → re-install the hook if user previously chose `n`
- `uninstall` → remove hook + MCP server config + skill registration
- `--version`, `--help`

### `middleware/src/bridge_launcher.ts` (NEW)

Encapsulates Python detection → venv resolution → bridge spawn → healthcheck → graceful shutdown. Eviction-safe (recreates venv if `pip` fails halfway). Returns the ephemeral port the bridge bound to.

### `middleware/src/index.ts` / `mcp_server.ts` (MODIFIED)

Existing MCP server logic. Two changes:
- Read bridge port from `bridge_launcher` instead of hard-coded 7523.
- Extend `aegis_read` to handle `.pdf` (via `pdf-parse`) and `.docx` (via `mammoth`); image extensions return `request_permission` without text extraction.

### `aegis/bridge.py` (MOVED from `aegis_bridge.py`)

Python HTTP server. Accepts `--port` (ephemeral), `--backend {local,ollama}` (default `local`). Otherwise unchanged from Phase 3b.

### `aegis/__init__.py` (NEW)

Empty marker file to make `aegis/` a proper Python package.

### `aegis/embedding.py` (UNCHANGED)

The `Embedder` wrapper around `sentence-transformers`. Already correct from Phase 3b.

### `aegis/head/lr.joblib` (MOVED from `aegis-head/lr.joblib`)

The 25 KB trained head. Bytes unchanged.

### `aegis/requirements.txt` (NEW)

Pinned Python dependencies for the bootstrap to install into `~/.aegis-mcp/venv/`:

```
sentence-transformers==3.0.0
scikit-learn==1.5.0
joblib==1.4.0
torch==2.10.0
numpy>=1.24,<3.0
```

(Exact pins to be locked at packaging time from the current `uv.lock`.)

### `skills/aegis/` (NEW)

Slash command skill registered with Claude Code. Layout:
- `SKILL.md` — skill manifest + one-paragraph description
- `commands/aegis-status.md` — implementation spec for `/aegis-status`
- `commands/aegis-policy.md` — `/aegis-policy`
- `commands/aegis-enable-hook.md` — `/aegis-enable-hook`
- `commands/aegis-disable-hook.md` — `/aegis-disable-hook`
- `commands/aegis-uninstall.md` — `/aegis-uninstall`
- `scripts/status.js`, `enable-hook.js`, `disable-hook.js`, `uninstall.js` — implementations called by the command spec files

### `scripts/hook-enforce.js` (NEW)

Tiny Node script invoked by the Claude Code `PreToolUse` hook. Reads the tool name + arguments from stdin (per Claude Code hook protocol), and if the tool is `Read`/`Glob`/`Grep`, exits with a message directing Claude to use `aegis_read` instead. Otherwise allows the call through.

### `docs/PRIVACY.md` (NEW)

Public-facing privacy promise with verification recipes:
1. No network calls at inference — `lsof -i` snippet, expected output
2. Weights are local — `ls ~/.cache/huggingface/hub/models--google--embeddinggemma-300m/` shows the cached files; classifier head is `~/.aegis-mcp/python/aegis/head/lr.joblib`
3. No telemetry — `grep -r posthog\|amplitude\|honeycomb middleware/dist/` returns nothing
4. Source for the curious — link to the repo for code audit

### `LICENSE` (NEW)

Standard MIT text, with copyright line for Christian Morales Panitz / project.

### `README.md` (REWRITTEN — root)

Marketplace-facing. Structure:
1. Hero — tagline, privacy promise, install command, demo GIF
2. What it does — 4 bullets, one per verdict class
3. Receipts — pointer to PRIVACY.md
4. How it works — short architecture diagram
5. Performance — 94.90% accuracy, ~78 ms latency, link to scorecard
6. Install & config — Claude Code MCP config snippet, prerequisites
7. Contributing / License / footer

### `middleware/README.md` (REWRITTEN)

Same audience as root README but middleware-specific (dev-facing instead of end-user-facing). Drops all DataGuard branding and Ollama references. Internal-only, not on the marketplace listing.

### `middleware/package.json` (MODIFIED)

- `name`: `dataguard` → `aegis-mcp`
- `version`: `1.0.0`
- `bin`: `{ "aegis-mcp": "dist/cli.js" }` — enables `npx aegis-mcp`
- `files`: `["dist/", "../aegis/", "skills/", "scripts/", "LICENSE", "README.md"]`
- Keep existing deps (`@modelcontextprotocol/sdk`, `pdf-parse`, `mammoth`, etc.)

### `middleware/openclaw.plugin.json` (MODIFIED)

Refresh metadata (drop "FunctionGemma" reference) but keep file present for OpenClaw compatibility. Not the primary distribution metadata.

### `assets/demo.gif` (NEW)

60-second screen recording showing the 5-scene flow defined in the brainstorming. ≤ 5 MB optimized via `gifsicle`.

### `pyproject.toml` (root) (MODIFIED)

- `name`: `deepmind-cactus` → `aegis-mcp-dev`
- `description`: replace "Add your description here" with a real one-liner (e.g., "Aegis MCP — on-device privacy classifier for AI agents")
- `[project.authors]`: real values
- `[project.urls]`: GitHub repo, issue tracker

Note: the root `pyproject.toml` is for the dev workspace. The end-user-facing Python deps are in `aegis/requirements.txt` (used by the bootstrap, not pyproject).

## Data flow — install

1. `npx aegis-mcp` invokes `middleware/dist/cli.js`.
2. CLI parses argv. No subcommand → install flow.
3. CLI prints consent prompt: "Add Aegis enforcement hook to ~/.claude/settings.json? [Y/n]"
4. On `Y` (or default): backup `~/.claude/settings.json` to `~/.aegis-mcp/backups/settings.json.<timestamp>`, additively insert the namespaced hook entry, write back.
5. CLI installs the skill: copy `skills/aegis/` to `~/.aegis-mcp/skills/aegis/`, add to Claude Code `extensions:` array.
6. CLI registers the MCP server in `~/.claude.json` (additively).
7. CLI starts `bridge_launcher`: detects Python, creates `~/.aegis-mcp/venv/`, `pip install -r aegis/requirements.txt`, spawns `aegis/bridge.py --port <ephemeral>`, polls `/health` until ready.
8. CLI starts the MCP server proper, forwards stdio to Claude Code.
9. User sees: "Aegis ready. Read/Glob/Grep now route through aegis_read. Try `/aegis-status` to verify."

## Data flow — runtime classification

Already documented in the architecture diagram above. Unchanged from Phase 3b internally; only the orchestration around it changes.

## Data flow — uninstall

`/aegis-uninstall` (or `npx aegis-mcp uninstall`):
1. Locate `aegis-mcp:enforce-read-routing` hook in `~/.claude/settings.json` by name (resilient to reordering); remove.
2. Remove Aegis entry from `~/.claude.json` `mcpServers`.
3. Remove skill from `extensions:` array.
4. Prompt: "Remove ~/.aegis-mcp/? Contains cached embedding model (~150 MB). [y/N]"
5. Print: "If you want your old settings.json back, restore from `~/.aegis-mcp/backups/settings.json.<timestamp>`."

## Error handling

- **Python not found** → print "Aegis requires Python 3.12+ on PATH" with install link; exit nonzero.
- **`pip install` fails in venv** → capture stderr, log to `~/.aegis-mcp/install.log`, exit with message pointing the user to the log.
- **Bridge healthcheck timeout (30s)** → kill child, capture bridge stderr to install.log, exit with message.
- **`~/.claude/settings.json` is malformed JSON** → leave config untouched, print error + restoration hint; exit nonzero. Don't try to "fix" it.
- **Existing hook with same name** → detect, print "Aegis hook already installed; nothing to do", exit 0.
- **Hook script can't reach bridge at runtime** → hook fails open with a warning logged (degraded: native Read works, Aegis isn't blocking). `/aegis-status` reports "bridge unreachable; reinstall via `npx aegis-mcp`".
- **Slash command can't find scripts** → command prints "Aegis appears to be partially uninstalled. Run `npx aegis-mcp` to reinstall."

## Testing

**Existing tests preserved** — all of Phase 3b/3b.5's tests continue to pass (`tests/test_train_head_cli.py`, `test_eval_fresh.py`, `test_eval_regression.py`, `test_prompt_sweep.py`, plus middleware existing tests).

**New tests for v1:**
- `middleware/tests/extract.test.ts` — PDF/DOCX text extraction; 12 fixtures (3 per verdict class); image files return `request_permission`; encrypted PDF rejection; oversize handling.
- `middleware/tests/installer.test.ts` — hook installer respects existing hooks; backup is created and timestamped; namespaced hook entry survives user reordering; uninstall removes only the namespaced entry.
- `middleware/tests/cli.test.ts` — `npx aegis-mcp` subcommands respond correctly (`install-hook`, `uninstall`, `--version`, `--help`).
- `tests/test_smoke_install.sh` — end-to-end smoke: fresh `tmp_home`, run `AEGIS_INSTALL_HOOK=1 npx aegis-mcp`, verify bridge healthcheck passes, classify a known file, then `npx aegis-mcp uninstall`. Asserts clean teardown.

**Out of scope for v1 testing:**
- Cross-platform CI (macOS only for v1; Linux/Windows is v1.1).
- Load testing.
- Adversarial input.

## Out of scope

Explicitly NOT in Phase 4:

- **OCR / image classification** — Phase 5; image files return `request_permission` for v1.
- **Cross-platform CI** (Linux, Windows) — v1.1; v1 ships macOS-first.
- **Active learning / telemetry** — conflicts with privacy promise.
- **Custom verdict classes** — v2 head feature (Phase 6+); current 4 classes are baked in.
- **Encrypted PDF support** — needs password UX; deferred.
- **Streaming bridge updates / hot reload** — bridge restarts on head update.
- **Multi-language UI** — v2; English-only for v1.
- **GPU acceleration** — CPU is fast enough at ~78 ms p50.
- **User-supplied embedding models** — EmbeddingGemma + LR head are tightly coupled; swapping requires retraining.
- **Phase 3b.5.1** — accuracy improvement parked per `docs/limits-and-improvements.md`; not blocking v1.

## Reviewable artifacts on completion

When v1 lands, the following are part of the deliverable:

1. `middleware/package.json` — published as `aegis-mcp@1.0.0` on npm
2. `middleware/dist/cli.js` + `dist/bridge_launcher.js` — install + bootstrap
3. `aegis/bridge.py`, `aegis/embedding.py`, `aegis/head/lr.joblib`, `aegis/requirements.txt` — packaged Python runtime
4. `skills/aegis/` — slash command skill
5. `scripts/hook-enforce.js` — the Read/Glob/Grep enforcement hook
6. `LICENSE` — MIT
7. `README.md` — public-facing, with hero + receipts + demo GIF + perf + install
8. `docs/PRIVACY.md` — the receipts
9. `assets/demo.gif` — 60-second flow
10. Git tag `v1.0.0`
11. npm publish completed
12. Anthropic MCP directory PR opened
13. Claude Code plugin marketplace submission filed

## Open re-decisions deferred to plan time

- Exact `~/.claude/settings.json` hook schema — verify against Claude Code's current docs at plan time.
- Exact slash-command skill registration mechanism — verify against Claude Code's current skill API at plan time.
- npm package `bin` invocation flow (`npx -y` vs `npx`) — pick at plan time based on what marketplace docs recommend.
- Demo GIF recording specifics — exact files used (from `samples/`), exact prompts shown, screen-recording tool — locked at recording time (Wave 3); the 5-scene structure is fixed but the concrete files are not.
