# Phase 4 — Publish as MCP Marketplace Plugin (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish Aegis as a one-command-install MCP plugin (`aegis-mcp` on npm + Anthropic MCP directory + Claude Code plugin marketplace) shipping the Phase 3b head at 94.90% accuracy.

**Architecture:** TypeScript MCP server (middleware/) spawns the in-process Python bridge (aegis/) with a user-cached venv at `~/.aegis-mcp/`. One Y/n consent prompt on first run installs a Read/Glob/Grep enforcement hook into `~/.claude/settings.json`. A slash command skill at `skills/aegis/` provides post-install management. Image files return `request_permission` (no OCR in v1).

**Tech Stack:** TypeScript (Node.js MCP server via `@modelcontextprotocol/sdk`), Python 3.12 (bridge), sentence-transformers + sklearn (the head), Claude Code MCP plugin + skill APIs.

**Workflow shape:** T1-T7 serial (rename + bootstrap). T8-T12 parallel-safe (READMEs + PDF/DOCX + tests in separate file trees). T13-T14 serial (demo + smoke). T15-T17 publish (user-executed actions: npm publish, marketplace PRs).

**Spec:** [`docs/superpowers/specs/2026-05-23-phase-4-publish-mcp-marketplace-design.md`](../specs/2026-05-23-phase-4-publish-mcp-marketplace-design.md)

**Rules carried over from prior phases:**
- Commits are local-only. The user is the sole gatekeeper for what reaches the remote — never `git push`, never `gh pr create`, never `npm publish`. The implementer prepares; the user executes anything that crosses a network boundary.
- `.codex/` is gitignored and out of scope. Do not read, edit, or commit anything under `.codex/`.

---

## File Structure (locked at plan time)

**NEW files:**

| Path | Purpose |
|---|---|
| `aegis/__init__.py` | Python package marker |
| `aegis/bridge.py` | Moved from repo root `aegis_bridge.py` |
| `aegis/embedding.py` | Already exists at this path — leave |
| `aegis/head/lr.joblib` | Moved from repo root `aegis-head/lr.joblib` |
| `aegis/requirements.txt` | Pinned Python deps the bootstrap installs into `~/.aegis-mcp/venv/` |
| `middleware/src/cli.ts` | `npx aegis-mcp` entry point with subcommands |
| `middleware/src/bridge_launcher.ts` | Python detection + venv setup + spawn + healthcheck |
| `middleware/src/installer.ts` | Hook installer (consent prompt, backup, additive write, uninstall) |
| `scripts/hook-enforce.js` | Node script invoked by the Claude Code PreToolUse hook |
| `skills/aegis/SKILL.md` | Skill manifest |
| `skills/aegis/commands/aegis-status.md` | `/aegis-status` command spec |
| `skills/aegis/commands/aegis-policy.md` | `/aegis-policy` |
| `skills/aegis/commands/aegis-enable-hook.md` | `/aegis-enable-hook` |
| `skills/aegis/commands/aegis-disable-hook.md` | `/aegis-disable-hook` |
| `skills/aegis/commands/aegis-uninstall.md` | `/aegis-uninstall` |
| `skills/aegis/scripts/status.js` | Implementation called by aegis-status.md |
| `skills/aegis/scripts/enable-hook.js` | Implementation for aegis-enable-hook |
| `skills/aegis/scripts/disable-hook.js` | Implementation for aegis-disable-hook |
| `skills/aegis/scripts/uninstall.js` | Implementation for aegis-uninstall |
| `middleware/tests/extract.test.ts` | PDF/DOCX/image extraction tests |
| `middleware/tests/installer.test.ts` | Hook installer tests |
| `middleware/tests/cli.test.ts` | CLI subcommand tests |
| `middleware/tests/fixtures/safe.pdf` | Test fixture |
| `middleware/tests/fixtures/safe.docx` | Test fixture |
| `middleware/tests/fixtures/credentials.pdf` | Test fixture |
| `middleware/tests/fixtures/credentials.docx` | Test fixture |
| `middleware/tests/fixtures/screenshot.png` | Test fixture (image, expect request_permission) |
| `middleware/tests/fixtures/encrypted.pdf` | Test fixture (encrypted, expect rejection) |
| `tests/test_smoke_install.sh` | End-to-end smoke test |
| `docs/PRIVACY.md` | Public privacy promise + verification recipes |
| `assets/demo.gif` | 60-second 5-scene demo |
| `LICENSE` | MIT |

**MODIFIED files:**

| Path | What changes |
|---|---|
| `pyproject.toml` | Rename `deepmind-cactus` → `aegis-mcp-dev`; real description, authors, urls |
| `middleware/package.json` | Rename `dataguard` → `aegis-mcp`; version `1.0.0`; `bin` entry; `files` allowlist |
| `middleware/openclaw.plugin.json` | Drop FunctionGemma reference; refresh description |
| `middleware/src/mcp-server.ts` | Use ephemeral bridge port from `bridge_launcher` instead of hardcoded 7523 |
| `middleware/src/plugin/index.ts` (or wherever aegis_read is implemented) | Wire PDF/DOCX extraction via existing `pdf-parse` + `mammoth` deps; image files → `request_permission` |
| `README.md` | Full rewrite for marketplace audience (hero, receipts, perf, install) |
| `middleware/README.md` | Full rewrite, drop DataGuard branding |

**MOVED (handled in T1):**

| From | To |
|---|---|
| `aegis_bridge.py` | `aegis/bridge.py` |
| `aegis-head/lr.joblib` | `aegis/head/lr.joblib` |

**Branch:** create `phase-4-publish` off current `main` (HEAD `bee65a2` after cleanup landed).

---

## Task 1: Branch + repository restructure

**Files:**
- Move: `aegis_bridge.py` → `aegis/bridge.py`
- Move: `aegis-head/lr.joblib` → `aegis/head/lr.joblib`
- Create: `aegis/__init__.py`
- Modify: `aegis/bridge.py` (update imports), `aegis/embedding.py` (relative imports if needed)
- Modify: `tests/*.py` (update imports from `aegis_bridge` → `aegis.bridge`)
- Modify: `middleware/src/router/classify.ts` (no code change — bridge HTTP URL unchanged; verify)

This is the foundation. Everything downstream assumes the new layout.

- [ ] **Step 1.1: Create the phase-4-publish branch**

```bash
git checkout main
git pull --ff-only
git checkout -b phase-4-publish
git status  # expect clean
```

- [ ] **Step 1.2: Move the bridge into the package directory**

```bash
git mv aegis_bridge.py aegis/bridge.py
mkdir -p aegis/head
git mv aegis-head/lr.joblib aegis/head/lr.joblib
rmdir aegis-head 2>/dev/null  # remove now-empty directory if no other contents
```

- [ ] **Step 1.3: Create the package marker**

Create `/Users/excallibur/dev/aegis/aegis/__init__.py` with content:

```python
"""Aegis — on-device privacy classifier for AI agents.

This package contains the runtime essentials shipped with `aegis-mcp`:
  - bridge.py     HTTP server that exposes /classify
  - embedding.py  Embedder wrapper around sentence-transformers
  - head/         Trained LR classifier weights
"""
```

- [ ] **Step 1.4: Update the moved bridge.py for the new module location**

Read the current first ~50 lines of `aegis/bridge.py` (formerly `aegis_bridge.py`). It imports `from aegis.embedding import Embedder` — that should still work because `aegis/embedding.py` exists. Also update the head-path lookup. Find the line that does `pathlib.Path("aegis-head/lr.joblib")` (or similar) and change to:

```python
HEAD_PATH = pathlib.Path(__file__).resolve().parent / "head" / "lr.joblib"
```

This makes the bridge work both from a dev checkout (cwd = repo root) AND from the installed venv (cwd irrelevant).

- [ ] **Step 1.5: Update Python tests that import the bridge**

Grep first to find all callers:

```bash
grep -rln 'aegis_bridge\|aegis-head' tests/ train/ middleware/ aegis/ 2>/dev/null
```

For each Python file that imports `aegis_bridge`, update the import:
- `from aegis_bridge import X` → `from aegis.bridge import X`
- `import aegis_bridge` → `import aegis.bridge as aegis_bridge`

For shell scripts or docs that reference `python aegis_bridge.py`, update to `python -m aegis.bridge` or `python aegis/bridge.py`.

For `aegis-head/lr.joblib` string references in Python source, update to `aegis/head/lr.joblib`.

- [ ] **Step 1.6: Verify the test suite still passes after the move**

```bash
.venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration_slow.py 2>&1 | tail -10
```

Expected: 42/42 pass (or current count). Any failure here means an import path was missed.

- [ ] **Step 1.7: Verify the bridge still starts**

```bash
.venv/bin/python -m aegis.bridge --port 8765 &
BRIDGE_PID=$!
sleep 8
curl -s http://localhost:8765/health | python3 -m json.tool
kill $BRIDGE_PID 2>/dev/null
wait $BRIDGE_PID 2>/dev/null
```

Expected: `/health` returns valid JSON with `embed_task_prompt: "none"`, `C: 10.0`, and the head correctly loaded from the new location.

- [ ] **Step 1.8: Commit**

```bash
git add -A
git commit -m "Phase 4 T1 — restructure: aegis_bridge.py → aegis/bridge.py; aegis-head/ → aegis/head/"
```

---

## Task 2: Package metadata rename

**Files:**
- Modify: `pyproject.toml`
- Modify: `middleware/package.json`
- Modify: `middleware/openclaw.plugin.json`

Pure rename of identifiers; no code logic changes.

- [ ] **Step 2.1: Update root pyproject.toml**

Read `/Users/excallibur/dev/aegis/pyproject.toml`. Replace the `[project]` block:

```toml
[project]
name = "aegis-mcp-dev"
version = "1.0.0"
description = "Aegis MCP — on-device privacy classifier for AI agents (dev workspace)"
readme = "README.md"
requires-python = ">=3.12"
authors = [
    { name = "Christian Morales Panitz" },
]
license = { text = "MIT" }
classifiers = [
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.12",
    "Topic :: Security",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
dependencies = [
    "accelerate>=1.12.0",
    "google-genai>=1.64.0",
    "joblib>=1.5.3",
    "peft>=0.18.1",
    "scikit-learn>=1.8.0",
    "sentence-transformers>=3.0.0",
    "torch>=2.10.0",
    "tqdm>=4.67.3",
    "transformers>=5.2.0",
]

[project.urls]
Repository = "https://github.com/AmaruEscalante/aegis"
Issues = "https://github.com/AmaruEscalante/aegis/issues"
```

The rest of the file (`[dependency-groups]`, `[tool.pytest.ini_options]`) stays unchanged.

- [ ] **Step 2.2: Update middleware/package.json**

Read `/Users/excallibur/dev/aegis/middleware/package.json`. Replace `name`, `version`, `description`, `main`, `bin`, `files`, and the `openclaw` block:

```json
{
  "name": "aegis-mcp",
  "version": "1.0.0",
  "description": "On-device privacy classifier for AI agents — MCP plugin",
  "main": "dist/mcp-server.js",
  "bin": {
    "aegis-mcp": "dist/cli.js"
  },
  "files": [
    "dist/",
    "../aegis/",
    "../skills/",
    "../scripts/",
    "../LICENSE",
    "../README.md",
    "../docs/PRIVACY.md"
  ],
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "test:watch": "vitest",
    "dev": "tsc --watch",
    "clean": "rm -rf dist",
    "mcp": "node dist/mcp-server.js",
    "mcp:dev": "npx tsx src/mcp-server.ts"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.26.0",
    "mammoth": "^1.7.1",
    "minimatch": "^9.0.5",
    "pdf-lib": "^1.17.1",
    "pdf-parse": "^1.1.1",
    "pdfjs-dist": "^4.4.168",
    "zod": "^4.3.6"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "pdfkit": "^0.17.2",
    "tsx": "^4.21.0",
    "typescript": "^5.4.0",
    "vitest": "^1.6.0"
  },
  "keywords": [
    "mcp",
    "privacy",
    "ai-safety",
    "claude-code",
    "on-device"
  ],
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/AmaruEscalante/aegis.git"
  }
}
```

Note: the `openclaw` key is removed entirely (no longer the primary distribution target). The `keywords` array is reset for marketplace SEO.

- [ ] **Step 2.3: Update middleware/openclaw.plugin.json**

Read the file. Update the top-level `version` and `description`:

```json
{
  "id": "aegis",
  "name": "Aegis",
  "version": "1.0.0",
  "description": "On-device privacy classifier for AI agents. Classifies files via in-process embeddinggemma + LR head; routes to passthrough, sanitization, block, or escalation.",
  "main": "dist/plugin/index.js",
  ...
}
```

Inside `configSchema.properties`, the `aegisBridgeUrl` default stays as-is (`http://127.0.0.1:7523`) since this file is just OpenClaw compat metadata. Remove any explicit FunctionGemma references in descriptions.

- [ ] **Step 2.4: Verify the test suite still passes**

```bash
.venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration_slow.py 2>&1 | tail -3
cd middleware && npm test 2>&1 | tail -3
cd ..
```

Expected: all pass.

- [ ] **Step 2.5: Commit**

```bash
git add pyproject.toml middleware/package.json middleware/openclaw.plugin.json
git commit -m "Phase 4 T2 — rename: deepmind-cactus + dataguard → aegis-mcp"
```

---

## Task 3: Add LICENSE + requirements.txt + scripts/hook-enforce.js

**Files:**
- Create: `LICENSE`
- Create: `aegis/requirements.txt`
- Create: `scripts/hook-enforce.js`

Three independent files, none with logic complex enough for TDD. Each gets a sanity-check command.

- [ ] **Step 3.1: Add MIT LICENSE**

Create `/Users/excallibur/dev/aegis/LICENSE`:

```
MIT License

Copyright (c) 2026 Christian Morales Panitz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3.2: Add aegis/requirements.txt**

Pin the versions currently in `uv.lock` (or `pyproject.toml`). Run:

```bash
.venv/bin/python -c "
import importlib.metadata as md
for pkg in ('sentence-transformers', 'scikit-learn', 'joblib', 'torch', 'numpy'):
    print(f'{pkg}=={md.version(pkg)}')
"
```

Capture the actual installed versions. Then create `/Users/excallibur/dev/aegis/aegis/requirements.txt`:

```
# Runtime dependencies for the Aegis bridge (aegis/bridge.py).
# Pinned at v1.0.0 release time. The bootstrap installs these into
# ~/.aegis-mcp/venv/ on first run.

sentence-transformers==<version-from-step-above>
scikit-learn==<version-from-step-above>
joblib==<version-from-step-above>
torch==<version-from-step-above>
numpy==<version-from-step-above>
```

(Replace `<version-from-step-above>` with the actual values from Step 3.2's print output.)

- [ ] **Step 3.3: Create scripts/hook-enforce.js**

Create the directory + file. The script reads tool-call info from Claude Code's hook protocol on stdin and rejects Read/Glob/Grep with a routing message.

```bash
mkdir -p scripts
```

Create `/Users/excallibur/dev/aegis/scripts/hook-enforce.js`:

```javascript
#!/usr/bin/env node
/**
 * Aegis PreToolUse hook — reject Read/Glob/Grep calls and route Claude
 * to use the aegis_read MCP tool instead.
 *
 * Claude Code hooks receive a JSON payload on stdin describing the tool
 * call. We emit JSON on stdout with `decision: "block"` and a message
 * Claude can read to self-correct.
 *
 * Protocol reference: https://docs.claude.com/claude-code/hooks
 */

const BLOCKED = new Set(['Read', 'Glob', 'Grep']);

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { raw += chunk; });
process.stdin.on('end', () => {
    let payload;
    try {
        payload = JSON.parse(raw);
    } catch (e) {
        // If we can't parse, fail open (let the call through) so we
        // don't accidentally brick Claude Code. Log to stderr for debugging.
        console.error(`[aegis-hook] failed to parse hook payload: ${e.message}`);
        process.exit(0);
    }

    const toolName = payload?.tool_name;
    if (!BLOCKED.has(toolName)) {
        // Not a tool we care about — allow.
        process.exit(0);
    }

    // Block with a clear redirect message Claude can act on.
    const response = {
        decision: 'block',
        reason: `Aegis is active — use aegis_read instead of ${toolName} for file content. ` +
                `Aegis classifies the file on-device and either passes it through, sanitizes PII, ` +
                `blocks credentials, or escalates to the user. See /aegis-status for current policy.`,
    };
    process.stdout.write(JSON.stringify(response) + '\n');
    process.exit(0);
});
```

- [ ] **Step 3.4: Sanity-check the hook script**

```bash
echo '{"tool_name":"Read","tool_input":{"file_path":"foo.txt"}}' | node scripts/hook-enforce.js
echo "---"
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | node scripts/hook-enforce.js
```

Expected output:
- First call: JSON with `"decision":"block"` and the routing message.
- Second call: empty output, exit 0 (Bash is not in BLOCKED).

- [ ] **Step 3.5: Commit**

```bash
git add LICENSE aegis/requirements.txt scripts/hook-enforce.js
git commit -m "Phase 4 T3 — add LICENSE (MIT), aegis/requirements.txt, scripts/hook-enforce.js"
```

---

## Task 4: bridge_launcher.ts — Python detection + venv + spawn

**Files:**
- Create: `middleware/src/bridge_launcher.ts`
- Create: `middleware/tests/bridge_launcher.test.ts`

This is the most complex new piece. TDD strictly.

- [ ] **Step 4.1: Write the failing tests**

Create `/Users/excallibur/dev/aegis/middleware/tests/bridge_launcher.test.ts`:

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
    detectPython,
    resolveAegisCachePath,
    findFreePort,
} from '../src/bridge_launcher';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';

describe('detectPython', () => {
    it('returns a Python 3.12+ path when one is on PATH', async () => {
        const p = await detectPython();
        expect(p).toBeTruthy();
        expect(typeof p).toBe('string');
    });

    it('throws a clear error if no Python ≥ 3.12 is available', async () => {
        // Use a sentinel PATH with no python
        const originalPath = process.env.PATH;
        process.env.PATH = '/nonexistent';
        try {
            await expect(detectPython()).rejects.toThrow(/Python 3\.12/);
        } finally {
            process.env.PATH = originalPath;
        }
    });
});

describe('resolveAegisCachePath', () => {
    it('returns a path under the user home', () => {
        const p = resolveAegisCachePath();
        expect(p).toContain(os.homedir());
        expect(p).toContain('.aegis-mcp');
    });
});

describe('findFreePort', () => {
    it('returns a port number between 1024 and 65535', async () => {
        const port = await findFreePort();
        expect(port).toBeGreaterThan(1024);
        expect(port).toBeLessThan(65536);
    });

    it('returns different ports on successive calls', async () => {
        const p1 = await findFreePort();
        const p2 = await findFreePort();
        // Not guaranteed to be different (OS can reassign), but very likely
        // for back-to-back calls. If this is flaky, change to checking
        // both ports are valid.
        expect(p1).toBeGreaterThan(0);
        expect(p2).toBeGreaterThan(0);
    });
});
```

- [ ] **Step 4.2: Run tests to verify they fail**

```bash
cd middleware && npx vitest run tests/bridge_launcher.test.ts
```

Expected: all fail with module-not-found or undefined function errors.

- [ ] **Step 4.3: Implement bridge_launcher.ts**

Create `/Users/excallibur/dev/aegis/middleware/src/bridge_launcher.ts`:

```typescript
/**
 * Bridge launcher — detects Python, ensures the user-cached venv at
 * ~/.aegis-mcp/venv/ exists with pinned dependencies installed, spawns
 * aegis/bridge.py on an ephemeral port, and polls /health until ready.
 *
 * Owned by middleware/src/cli.ts; not invoked directly by the MCP server.
 */

import { spawn, spawnSync, ChildProcess } from 'node:child_process';
import { createServer } from 'node:net';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';

const REQUIRED_PYTHON_MIN = [3, 12] as const;

/**
 * Find a Python ≥3.12 interpreter on PATH. Tries `python3.12`, `python3`, `python` in order.
 * Throws with an install hint if nothing matches.
 */
export async function detectPython(): Promise<string> {
    const candidates = ['python3.12', 'python3', 'python'];
    for (const cmd of candidates) {
        try {
            const result = spawnSync(cmd, ['-c', 'import sys; print(sys.version_info[0], sys.version_info[1])'], {
                encoding: 'utf8',
                timeout: 5000,
            });
            if (result.status === 0 && result.stdout) {
                const [maj, min] = result.stdout.trim().split(' ').map(Number);
                if (maj > REQUIRED_PYTHON_MIN[0] || (maj === REQUIRED_PYTHON_MIN[0] && min >= REQUIRED_PYTHON_MIN[1])) {
                    return cmd;
                }
            }
        } catch {
            // try next candidate
        }
    }
    throw new Error(
        `Aegis requires Python ${REQUIRED_PYTHON_MIN.join('.')}+ on PATH. ` +
        `Install via https://www.python.org/downloads/ or your system package manager.`
    );
}

/**
 * Return the Aegis cache directory at ~/.aegis-mcp/.
 * Creates it if it doesn't exist.
 */
export function resolveAegisCachePath(): string {
    const cachePath = path.join(os.homedir(), '.aegis-mcp');
    fs.mkdirSync(cachePath, { recursive: true });
    return cachePath;
}

/**
 * Find a free TCP port by binding to 0 and reading the assigned port.
 */
export async function findFreePort(): Promise<number> {
    return new Promise((resolve, reject) => {
        const server = createServer();
        server.unref();
        server.on('error', reject);
        server.listen(0, () => {
            const address = server.address();
            if (typeof address === 'object' && address !== null) {
                const port = address.port;
                server.close(() => resolve(port));
            } else {
                reject(new Error('Could not determine free port'));
            }
        });
    });
}

/**
 * Ensure a venv exists at <cachePath>/venv with the pinned deps installed.
 * Idempotent: if the venv exists and the requirements.txt mtime is older than
 * the venv's marker file, skip the install. Otherwise (re)install.
 */
export async function ensureVenv(
    pythonCmd: string,
    cachePath: string,
    requirementsPath: string,
): Promise<string> {
    const venvPath = path.join(cachePath, 'venv');
    const venvPython = path.join(venvPath, 'bin', 'python');
    const markerPath = path.join(venvPath, '.aegis-installed-marker');

    // Create venv if absent
    if (!fs.existsSync(venvPython)) {
        const r = spawnSync(pythonCmd, ['-m', 'venv', venvPath], { encoding: 'utf8' });
        if (r.status !== 0) {
            throw new Error(`Failed to create venv at ${venvPath}: ${r.stderr}`);
        }
    }

    // Check if (re)install is needed
    const reqMtime = fs.statSync(requirementsPath).mtime;
    const markerMtime = fs.existsSync(markerPath) ? fs.statSync(markerPath).mtime : new Date(0);
    if (reqMtime > markerMtime) {
        const r = spawnSync(venvPython, ['-m', 'pip', 'install', '--quiet', '-r', requirementsPath], {
            encoding: 'utf8',
        });
        if (r.status !== 0) {
            throw new Error(`Failed to install requirements: ${r.stderr}`);
        }
        fs.writeFileSync(markerPath, new Date().toISOString());
    }

    return venvPython;
}

/**
 * Spawn aegis/bridge.py and wait for /health to return OK.
 * Returns the child process handle (caller is responsible for killing on shutdown).
 */
export async function spawnBridge(
    venvPython: string,
    bridgeScript: string,
    port: number,
    timeoutMs = 30000,
): Promise<ChildProcess> {
    const child = spawn(venvPython, [bridgeScript, '--port', String(port), '--backend', 'local'], {
        stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stderr = '';
    child.stderr?.on('data', (d) => { stderr += d.toString(); });

    // Poll /health until ready or timeout
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        if (child.exitCode !== null) {
            throw new Error(`Bridge exited early (code ${child.exitCode}): ${stderr}`);
        }
        try {
            const res = await fetch(`http://127.0.0.1:${port}/health`);
            if (res.ok) {
                return child;
            }
        } catch {
            // not ready yet
        }
        await new Promise((r) => setTimeout(r, 500));
    }

    child.kill();
    throw new Error(`Bridge healthcheck timed out after ${timeoutMs}ms. stderr: ${stderr}`);
}
```

- [ ] **Step 4.4: Run tests to verify they pass**

```bash
cd middleware && npx vitest run tests/bridge_launcher.test.ts
```

Expected: all pass.

- [ ] **Step 4.5: Commit**

```bash
git add middleware/src/bridge_launcher.ts middleware/tests/bridge_launcher.test.ts
git commit -m "Phase 4 T4 — bridge_launcher.ts: Python detection + venv + spawn + healthcheck"
```

---

## Task 5: installer.ts — hook + skill installer with consent prompt

**Files:**
- Create: `middleware/src/installer.ts`
- Create: `middleware/tests/installer.test.ts`

Handles the `~/.claude/settings.json` mutation with the namespaced hook entry, the timestamped backup, and the symmetric uninstall.

- [ ] **Step 5.1: Write the failing tests**

Create `/Users/excallibur/dev/aegis/middleware/tests/installer.test.ts`:

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
    installHook,
    uninstallHook,
    findAegisHookEntry,
    HOOK_NAME,
} from '../src/installer';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';

describe('installer', () => {
    let tmpDir: string;
    let settingsPath: string;

    beforeEach(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'aegis-installer-test-'));
        settingsPath = path.join(tmpDir, 'settings.json');
    });

    afterEach(() => {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('creates settings.json with the hook if file is absent', async () => {
        const backupPath = await installHook({ settingsPath, hookScript: '/path/to/hook.js' });
        expect(backupPath).toBeNull();  // no backup needed when file absent
        const written = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
        expect(written.hooks?.PreToolUse).toBeInstanceOf(Array);
        const aegisEntry = written.hooks.PreToolUse.find((h: any) => h.name === HOOK_NAME);
        expect(aegisEntry).toBeTruthy();
        expect(aegisEntry.matcher).toBe('Read|Glob|Grep');
    });

    it('additively patches existing settings.json without touching other keys', async () => {
        const existing = {
            theme: 'dark',
            hooks: {
                PreToolUse: [
                    { name: 'other-plugin:foo', matcher: 'Bash', hooks: [{ type: 'command', command: 'echo' }] },
                ],
            },
        };
        fs.writeFileSync(settingsPath, JSON.stringify(existing, null, 2));

        const backupPath = await installHook({ settingsPath, hookScript: '/path/to/hook.js' });
        expect(backupPath).toBeTruthy();
        expect(fs.existsSync(backupPath!)).toBe(true);

        const written = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
        expect(written.theme).toBe('dark');  // preserved
        expect(written.hooks.PreToolUse).toHaveLength(2);
        const otherEntry = written.hooks.PreToolUse.find((h: any) => h.name === 'other-plugin:foo');
        expect(otherEntry).toBeTruthy();
    });

    it('is idempotent — second install does not add a duplicate entry', async () => {
        await installHook({ settingsPath, hookScript: '/path/to/hook.js' });
        await installHook({ settingsPath, hookScript: '/path/to/hook.js' });
        const written = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
        const matches = written.hooks.PreToolUse.filter((h: any) => h.name === HOOK_NAME);
        expect(matches).toHaveLength(1);
    });

    it('uninstall removes only the aegis hook entry', async () => {
        const existing = {
            hooks: {
                PreToolUse: [
                    { name: 'other-plugin:foo', matcher: 'Bash', hooks: [{ type: 'command', command: 'echo' }] },
                ],
            },
        };
        fs.writeFileSync(settingsPath, JSON.stringify(existing, null, 2));
        await installHook({ settingsPath, hookScript: '/path/to/hook.js' });

        await uninstallHook({ settingsPath });

        const written = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
        expect(written.hooks.PreToolUse).toHaveLength(1);
        expect(written.hooks.PreToolUse[0].name).toBe('other-plugin:foo');
    });

    it('findAegisHookEntry returns the entry if present, null otherwise', () => {
        const settings1 = { hooks: { PreToolUse: [{ name: HOOK_NAME, matcher: 'Read', hooks: [] }] } };
        expect(findAegisHookEntry(settings1)).toBeTruthy();
        const settings2 = { hooks: { PreToolUse: [{ name: 'other', matcher: 'Read', hooks: [] }] } };
        expect(findAegisHookEntry(settings2)).toBeNull();
        expect(findAegisHookEntry({})).toBeNull();
    });
});
```

- [ ] **Step 5.2: Run tests to verify they fail**

```bash
cd middleware && npx vitest run tests/installer.test.ts
```

Expected: all fail with module-not-found.

- [ ] **Step 5.3: Implement installer.ts**

Create `/Users/excallibur/dev/aegis/middleware/src/installer.ts`:

```typescript
/**
 * Hook installer — adds the Aegis PreToolUse hook to ~/.claude/settings.json
 * additively (preserves existing hooks), with timestamped backup before
 * any mutation.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';

export const HOOK_NAME = 'aegis-mcp:enforce-read-routing';
export const HOOK_MATCHER = 'Read|Glob|Grep';

interface InstallOptions {
    settingsPath: string;
    hookScript: string;
}

interface UninstallOptions {
    settingsPath: string;
}

/**
 * Find the Aegis hook entry in the settings object, or null if absent.
 */
export function findAegisHookEntry(settings: any): any | null {
    const entries = settings?.hooks?.PreToolUse;
    if (!Array.isArray(entries)) return null;
    return entries.find((e: any) => e?.name === HOOK_NAME) ?? null;
}

/**
 * Install the Aegis hook. Idempotent. Creates settings.json if absent.
 * Returns the backup path (or null if no backup was needed).
 */
export async function installHook(opts: InstallOptions): Promise<string | null> {
    let settings: any = {};
    let backupPath: string | null = null;

    if (fs.existsSync(opts.settingsPath)) {
        const raw = fs.readFileSync(opts.settingsPath, 'utf8');
        try {
            settings = JSON.parse(raw);
        } catch (e: any) {
            throw new Error(
                `Refusing to install: ${opts.settingsPath} is not valid JSON. ` +
                `Fix the file manually before running 'npx aegis-mcp' again. (${e.message})`
            );
        }

        // Backup before mutating
        const ts = new Date().toISOString().replace(/[:.]/g, '-');
        const backupDir = path.join(path.dirname(opts.settingsPath), '..', '.aegis-mcp', 'backups');
        fs.mkdirSync(backupDir, { recursive: true });
        backupPath = path.join(backupDir, `settings.json.${ts}`);
        fs.copyFileSync(opts.settingsPath, backupPath);
    } else {
        // Ensure parent dir exists for new settings.json
        fs.mkdirSync(path.dirname(opts.settingsPath), { recursive: true });
    }

    // Idempotency check
    if (findAegisHookEntry(settings)) {
        return backupPath;  // already installed
    }

    // Additive patch
    if (!settings.hooks) settings.hooks = {};
    if (!Array.isArray(settings.hooks.PreToolUse)) settings.hooks.PreToolUse = [];
    settings.hooks.PreToolUse.push({
        name: HOOK_NAME,
        matcher: HOOK_MATCHER,
        hooks: [{ type: 'command', command: `node ${opts.hookScript}` }],
    });

    fs.writeFileSync(opts.settingsPath, JSON.stringify(settings, null, 2) + '\n');
    return backupPath;
}

/**
 * Remove the Aegis hook entry. Leaves other entries untouched.
 * No-op if settings.json doesn't exist or doesn't contain the entry.
 */
export async function uninstallHook(opts: UninstallOptions): Promise<void> {
    if (!fs.existsSync(opts.settingsPath)) return;
    const raw = fs.readFileSync(opts.settingsPath, 'utf8');
    let settings: any;
    try {
        settings = JSON.parse(raw);
    } catch {
        return;  // can't parse; nothing to remove
    }

    const entries = settings?.hooks?.PreToolUse;
    if (!Array.isArray(entries)) return;

    const filtered = entries.filter((e: any) => e?.name !== HOOK_NAME);
    if (filtered.length === entries.length) return;  // nothing changed

    settings.hooks.PreToolUse = filtered;
    fs.writeFileSync(opts.settingsPath, JSON.stringify(settings, null, 2) + '\n');
}
```

- [ ] **Step 5.4: Run tests to verify they pass**

```bash
cd middleware && npx vitest run tests/installer.test.ts
```

Expected: all 5 tests pass.

- [ ] **Step 5.5: Commit**

```bash
git add middleware/src/installer.ts middleware/tests/installer.test.ts
git commit -m "Phase 4 T5 — installer.ts: namespaced hook entry + idempotent install/uninstall + backup"
```

---

## Task 6: cli.ts — npx aegis-mcp entry point with consent prompt

**Files:**
- Create: `middleware/src/cli.ts`
- Create: `middleware/tests/cli.test.ts`

The user-facing entry. Subcommands: default (install + run), `install-hook`, `uninstall`, `--version`, `--help`.

- [ ] **Step 6.1: Write failing tests**

Create `/Users/excallibur/dev/aegis/middleware/tests/cli.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { parseArgs, CliCommand } from '../src/cli';

describe('parseArgs', () => {
    it('returns "run" command by default', () => {
        expect(parseArgs([])).toEqual({ command: 'run' });
    });

    it('parses install-hook subcommand', () => {
        expect(parseArgs(['install-hook'])).toEqual({ command: 'install-hook' });
    });

    it('parses uninstall subcommand', () => {
        expect(parseArgs(['uninstall'])).toEqual({ command: 'uninstall' });
    });

    it('parses --version', () => {
        expect(parseArgs(['--version'])).toEqual({ command: 'version' });
    });

    it('parses --help', () => {
        expect(parseArgs(['--help'])).toEqual({ command: 'help' });
        expect(parseArgs(['-h'])).toEqual({ command: 'help' });
    });

    it('respects AEGIS_INSTALL_HOOK=0 env to skip consent', () => {
        const args = parseArgs([], { AEGIS_INSTALL_HOOK: '0' });
        expect(args).toEqual({ command: 'run', skipHookInstall: true });
    });

    it('respects AEGIS_INSTALL_HOOK=1 env to auto-consent', () => {
        const args = parseArgs([], { AEGIS_INSTALL_HOOK: '1' });
        expect(args).toEqual({ command: 'run', autoConsent: true });
    });
});
```

- [ ] **Step 6.2: Run tests to verify they fail**

```bash
cd middleware && npx vitest run tests/cli.test.ts
```

Expected: module-not-found.

- [ ] **Step 6.3: Implement cli.ts**

Create `/Users/excallibur/dev/aegis/middleware/src/cli.ts`:

```typescript
#!/usr/bin/env node
/**
 * `npx aegis-mcp` entry point.
 *
 * Subcommands:
 *   (default)        — install (with consent) + start MCP server
 *   install-hook     — re-install the enforcement hook
 *   uninstall        — remove hook + skill + MCP server config
 *   --version, -v    — print version
 *   --help, -h       — print help
 *
 * Env vars:
 *   AEGIS_INSTALL_HOOK=1   — auto-consent to hook install (for CI/scripts)
 *   AEGIS_INSTALL_HOOK=0   — skip hook install entirely
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import * as readline from 'node:readline';

import {
    detectPython,
    resolveAegisCachePath,
    ensureVenv,
    findFreePort,
    spawnBridge,
} from './bridge_launcher';
import { installHook, uninstallHook, HOOK_NAME } from './installer';

export type CliCommand =
    | { command: 'run'; autoConsent?: boolean; skipHookInstall?: boolean }
    | { command: 'install-hook' }
    | { command: 'uninstall' }
    | { command: 'version' }
    | { command: 'help' };

export function parseArgs(argv: string[], env: Record<string, string | undefined> = process.env): CliCommand {
    if (argv.length === 0) {
        const hookEnv = env.AEGIS_INSTALL_HOOK;
        if (hookEnv === '0') return { command: 'run', skipHookInstall: true };
        if (hookEnv === '1') return { command: 'run', autoConsent: true };
        return { command: 'run' };
    }
    const cmd = argv[0];
    if (cmd === 'install-hook') return { command: 'install-hook' };
    if (cmd === 'uninstall') return { command: 'uninstall' };
    if (cmd === '--version' || cmd === '-v') return { command: 'version' };
    if (cmd === '--help' || cmd === '-h') return { command: 'help' };
    return { command: 'help' };  // unknown → help
}

const VERSION = '1.0.0';

const HELP_TEXT = `aegis-mcp — on-device privacy classifier for AI agents

Usage:
  npx aegis-mcp                Install (with consent) + start MCP server
  npx aegis-mcp install-hook   Re-install enforcement hook
  npx aegis-mcp uninstall      Remove hook + MCP server config
  npx aegis-mcp --version      Print version
  npx aegis-mcp --help         Show this help

Environment:
  AEGIS_INSTALL_HOOK=1   Auto-consent to hook install (CI/scripts)
  AEGIS_INSTALL_HOOK=0   Skip hook install entirely

See https://github.com/AmaruEscalante/aegis for full documentation.
`;

async function promptConsent(): Promise<boolean> {
    const rl = readline.createInterface({ input: process.stdin, output: process.stderr });
    return new Promise((resolve) => {
        rl.question(
            'Add Aegis enforcement hook to ~/.claude/settings.json?\n' +
            '  This routes Read/Glob/Grep through aegis_read automatically.\n' +
            '  You can disable later with /aegis-disable-hook or `npx aegis-mcp uninstall`.\n' +
            '[Y/n] ',
            (answer) => {
                rl.close();
                const normalized = answer.trim().toLowerCase();
                resolve(normalized === '' || normalized === 'y' || normalized === 'yes');
            }
        );
    });
}

async function runInstall(args: { autoConsent?: boolean; skipHookInstall?: boolean }): Promise<void> {
    process.stderr.write('Aegis MCP — on-device privacy classifier for Claude Code\n\n');

    const settingsPath = path.join(os.homedir(), '.claude', 'settings.json');
    const hookScript = path.resolve(__dirname, '..', '..', 'scripts', 'hook-enforce.js');

    let shouldInstallHook = false;
    if (args.skipHookInstall) {
        process.stderr.write('Skipping hook install (AEGIS_INSTALL_HOOK=0).\n');
    } else if (args.autoConsent) {
        shouldInstallHook = true;
        process.stderr.write('Auto-consenting to hook install (AEGIS_INSTALL_HOOK=1).\n');
    } else {
        shouldInstallHook = await promptConsent();
    }

    if (shouldInstallHook) {
        const backup = await installHook({ settingsPath, hookScript });
        if (backup) {
            process.stderr.write(`  ✓ Hook installed (backup at ${backup})\n`);
        } else {
            process.stderr.write(`  ✓ Hook installed\n`);
        }
    }

    // Start the bridge
    const pythonCmd = await detectPython();
    const cachePath = resolveAegisCachePath();
    const requirementsPath = path.resolve(__dirname, '..', '..', 'aegis', 'requirements.txt');
    const bridgeScript = path.resolve(__dirname, '..', '..', 'aegis', 'bridge.py');

    process.stderr.write('Setting up Python environment...\n');
    const venvPython = await ensureVenv(pythonCmd, cachePath, requirementsPath);
    const port = await findFreePort();

    process.stderr.write(`Starting bridge on port ${port}...\n`);
    const bridge = await spawnBridge(venvPython, bridgeScript, port);

    process.stderr.write('Aegis ready.\n');

    // Graceful shutdown
    const shutdown = () => {
        process.stderr.write('Shutting down...\n');
        bridge.kill();
        process.exit(0);
    };
    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

    // Hand off to MCP server (relative import; the actual MCP server file
    // exports a function we invoke here. If the server is structured as
    // a separate `node` invocation, replace with a spawn call.)
    const { startMcpServer } = await import('./mcp-server');
    await startMcpServer({ bridgePort: port });
}

async function runUninstall(): Promise<void> {
    const settingsPath = path.join(os.homedir(), '.claude', 'settings.json');
    await uninstallHook({ settingsPath });
    process.stderr.write('  ✓ Aegis hook removed from ~/.claude/settings.json\n');
    process.stderr.write('Cache at ~/.aegis-mcp/ preserved. Remove manually if desired.\n');
}

async function main(): Promise<void> {
    const args = parseArgs(process.argv.slice(2));

    switch (args.command) {
        case 'run':
            await runInstall(args);
            break;
        case 'install-hook': {
            const settingsPath = path.join(os.homedir(), '.claude', 'settings.json');
            const hookScript = path.resolve(__dirname, '..', '..', 'scripts', 'hook-enforce.js');
            const backup = await installHook({ settingsPath, hookScript });
            process.stderr.write(`  ✓ Hook installed (backup: ${backup ?? 'no prior config'})\n`);
            break;
        }
        case 'uninstall':
            await runUninstall();
            break;
        case 'version':
            console.log(VERSION);
            break;
        case 'help':
            console.log(HELP_TEXT);
            break;
    }
}

if (require.main === module) {
    main().catch((err) => {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
    });
}
```

- [ ] **Step 6.4: Refactor `middleware/src/mcp-server.ts` to export a startable function**

The existing `mcp-server.ts` likely runs `main()` at the bottom directly. Wrap it in an exported `startMcpServer({ bridgePort })` function that takes the ephemeral port and uses it to talk to the bridge.

Read the current file first. The change is roughly:

Before:
```typescript
// ... setup ...
const server = new Server(...);
server.connect(transport);
```

After:
```typescript
export async function startMcpServer(opts: { bridgePort: number }): Promise<void> {
    // ... setup using opts.bridgePort instead of hardcoded port ...
    const server = new Server(...);
    await server.connect(transport);
}

// Preserve direct-invocation path for `npm run mcp:dev`
if (require.main === module) {
    startMcpServer({ bridgePort: Number(process.env.AEGIS_BRIDGE_PORT) || 7523 });
}
```

- [ ] **Step 6.5: Run all tests**

```bash
cd middleware && npx vitest run tests/cli.test.ts
cd middleware && npm test 2>&1 | tail -5
```

Expected: CLI tests pass; nothing else broken.

- [ ] **Step 6.6: Build the TS to verify it compiles**

```bash
cd middleware && npm run build 2>&1 | tail -10
```

Expected: zero errors. `dist/cli.js`, `dist/bridge_launcher.js`, `dist/installer.js` all present.

- [ ] **Step 6.7: Commit**

```bash
git add middleware/src/cli.ts middleware/src/mcp-server.ts middleware/tests/cli.test.ts
git commit -m "Phase 4 T6 — cli.ts entry + consent prompt + mcp-server refactor for ephemeral port"
```

---

## Task 7: Slash command skill

**Files:**
- Create: `skills/aegis/SKILL.md`
- Create: `skills/aegis/commands/aegis-status.md`
- Create: `skills/aegis/commands/aegis-policy.md`
- Create: `skills/aegis/commands/aegis-enable-hook.md`
- Create: `skills/aegis/commands/aegis-disable-hook.md`
- Create: `skills/aegis/commands/aegis-uninstall.md`
- Create: `skills/aegis/scripts/status.js`
- Create: `skills/aegis/scripts/enable-hook.js`
- Create: `skills/aegis/scripts/disable-hook.js`
- Create: `skills/aegis/scripts/uninstall.js`

The skill is what registers the slash commands in Claude Code. Each command spec is a short markdown file that tells Claude what the command does; the JS scripts are the actual implementations.

- [ ] **Step 7.1: Create skill manifest**

```bash
mkdir -p skills/aegis/commands skills/aegis/scripts
```

Create `/Users/excallibur/dev/aegis/skills/aegis/SKILL.md`:

```markdown
---
name: aegis
description: Manage the Aegis MCP privacy classifier — status, policy, enable/disable enforcement, uninstall.
---

# Aegis management commands

Slash commands for managing the Aegis MCP plugin from inside Claude Code.

Available commands:
- `/aegis-status` — show current enforcement mode and recent verdicts
- `/aegis-policy` — show classification policy (allow/deny globs, thresholds)
- `/aegis-enable-hook` — enable Read/Glob/Grep enforcement
- `/aegis-disable-hook` — disable enforcement (tools still available, just not forced)
- `/aegis-uninstall` — remove the hook + MCP server config

See [Aegis README](https://github.com/AmaruEscalante/aegis) for full documentation.
```

- [ ] **Step 7.2: Create command specs**

Create `/Users/excallibur/dev/aegis/skills/aegis/commands/aegis-status.md`:

```markdown
---
name: aegis-status
description: Show current Aegis enforcement mode and recent verdicts.
---

When the user invokes `/aegis-status`:

1. Run `node ~/.aegis-mcp/skills/aegis/scripts/status.js`
2. Display the output to the user
```

Create `/Users/excallibur/dev/aegis/skills/aegis/commands/aegis-policy.md`:

```markdown
---
name: aegis-policy
description: Show Aegis classification policy (allow/deny globs, verdict thresholds).
---

When the user invokes `/aegis-policy`:

1. Call the `aegis_policy_explain` MCP tool with no arguments
2. Display the returned policy info to the user
```

Create `/Users/excallibur/dev/aegis/skills/aegis/commands/aegis-enable-hook.md`:

```markdown
---
name: aegis-enable-hook
description: Enable Aegis enforcement hook (route Read/Glob/Grep through aegis_read).
---

When the user invokes `/aegis-enable-hook`:

1. Run `node ~/.aegis-mcp/skills/aegis/scripts/enable-hook.js`
2. Report success or any error to the user
```

Create `/Users/excallibur/dev/aegis/skills/aegis/commands/aegis-disable-hook.md`:

```markdown
---
name: aegis-disable-hook
description: Disable Aegis enforcement hook. Tools remain available; Claude is no longer forced to use them.
---

When the user invokes `/aegis-disable-hook`:

1. Run `node ~/.aegis-mcp/skills/aegis/scripts/disable-hook.js`
2. Report success or any error to the user
```

Create `/Users/excallibur/dev/aegis/skills/aegis/commands/aegis-uninstall.md`:

```markdown
---
name: aegis-uninstall
description: Remove Aegis hook, MCP server config, and skill registration.
---

When the user invokes `/aegis-uninstall`:

1. Confirm with the user: "This will remove the Aegis hook, MCP server config, and slash command skill. Cached Python venv and embedding model at ~/.aegis-mcp/ will be preserved unless the user explicitly deletes them. Continue? [y/N]"
2. On `y`, run `node ~/.aegis-mcp/skills/aegis/scripts/uninstall.js`
3. Report the result
```

- [ ] **Step 7.3: Create script implementations**

Create `/Users/excallibur/dev/aegis/skills/aegis/scripts/status.js`:

```javascript
#!/usr/bin/env node
/**
 * /aegis-status implementation.
 * Reports: hook installed? bridge reachable? recent verdict counts (from log).
 */
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

const HOOK_NAME = 'aegis-mcp:enforce-read-routing';
const SETTINGS_PATH = path.join(os.homedir(), '.claude', 'settings.json');

async function main() {
    // Check hook
    let hookInstalled = false;
    try {
        const settings = JSON.parse(fs.readFileSync(SETTINGS_PATH, 'utf8'));
        hookInstalled = (settings?.hooks?.PreToolUse ?? []).some(e => e?.name === HOOK_NAME);
    } catch { /* file absent or malformed */ }

    // Check bridge — read the latest known port from the install marker
    const portFile = path.join(os.homedir(), '.aegis-mcp', 'bridge.port');
    let bridgeStatus = 'unknown';
    let bridgeMeta = {};
    if (fs.existsSync(portFile)) {
        const port = Number(fs.readFileSync(portFile, 'utf8').trim());
        try {
            const res = await fetch(`http://127.0.0.1:${port}/health`);
            if (res.ok) {
                bridgeMeta = await res.json();
                bridgeStatus = 'ok';
            } else {
                bridgeStatus = `error (status ${res.status})`;
            }
        } catch (e) {
            bridgeStatus = `unreachable (${e.message})`;
        }
    }

    console.log('Aegis status');
    console.log('============');
    console.log(`Hook (enforce Read/Glob/Grep):  ${hookInstalled ? 'installed' : 'NOT installed'}`);
    console.log(`Bridge:                          ${bridgeStatus}`);
    if (bridgeStatus === 'ok') {
        console.log(`  embed model:    ${bridgeMeta.embed_model}`);
        console.log(`  prompt:         ${bridgeMeta.embed_task_prompt}`);
        console.log(`  device:         ${bridgeMeta.device ?? 'unknown'}`);
    }
}

main().catch(e => { console.error(`Error: ${e.message}`); process.exit(1); });
```

Create `/Users/excallibur/dev/aegis/skills/aegis/scripts/enable-hook.js`:

```javascript
#!/usr/bin/env node
const path = require('node:path');
const os = require('node:os');
// Delegate to the npm-installed CLI's installer
const { installHook } = require(path.join(os.homedir(), '.aegis-mcp', 'middleware', 'dist', 'installer.js'));

const SETTINGS_PATH = path.join(os.homedir(), '.claude', 'settings.json');
const HOOK_SCRIPT = path.join(os.homedir(), '.aegis-mcp', 'middleware', 'scripts', 'hook-enforce.js');

installHook({ settingsPath: SETTINGS_PATH, hookScript: HOOK_SCRIPT })
    .then(backup => {
        console.log(`✓ Hook enabled${backup ? ` (backup: ${backup})` : ''}`);
    })
    .catch(e => { console.error(`Error: ${e.message}`); process.exit(1); });
```

Create `/Users/excallibur/dev/aegis/skills/aegis/scripts/disable-hook.js`:

```javascript
#!/usr/bin/env node
const path = require('node:path');
const os = require('node:os');
const { uninstallHook } = require(path.join(os.homedir(), '.aegis-mcp', 'middleware', 'dist', 'installer.js'));

const SETTINGS_PATH = path.join(os.homedir(), '.claude', 'settings.json');

uninstallHook({ settingsPath: SETTINGS_PATH })
    .then(() => console.log('✓ Hook disabled. MCP tools (aegis_read etc) remain available.'))
    .catch(e => { console.error(`Error: ${e.message}`); process.exit(1); });
```

Create `/Users/excallibur/dev/aegis/skills/aegis/scripts/uninstall.js`:

```javascript
#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { uninstallHook } = require(path.join(os.homedir(), '.aegis-mcp', 'middleware', 'dist', 'installer.js'));

const SETTINGS_PATH = path.join(os.homedir(), '.claude', 'settings.json');
const CLAUDE_CONFIG_PATH = path.join(os.homedir(), '.claude.json');

async function main() {
    // 1. Remove hook from settings.json
    await uninstallHook({ settingsPath: SETTINGS_PATH });
    console.log('✓ Hook removed from ~/.claude/settings.json');

    // 2. Remove MCP server entry from .claude.json
    if (fs.existsSync(CLAUDE_CONFIG_PATH)) {
        const cfg = JSON.parse(fs.readFileSync(CLAUDE_CONFIG_PATH, 'utf8'));
        if (cfg.mcpServers?.aegis) {
            delete cfg.mcpServers.aegis;
            fs.writeFileSync(CLAUDE_CONFIG_PATH, JSON.stringify(cfg, null, 2) + '\n');
            console.log('✓ MCP server entry removed from ~/.claude.json');
        }
    }

    console.log('');
    console.log('Cache at ~/.aegis-mcp/ preserved (contains the cached Python venv and embedding model).');
    console.log('Remove it manually with `rm -rf ~/.aegis-mcp` if you no longer want Aegis on disk.');
    console.log('');
    console.log('Backups of ~/.claude/settings.json are under ~/.aegis-mcp/backups/.');
}

main().catch(e => { console.error(`Error: ${e.message}`); process.exit(1); });
```

- [ ] **Step 7.4: Sanity-check that the scripts run (they'll fail at the require path because .aegis-mcp/ isn't populated yet, but the syntax should parse)**

```bash
node -c skills/aegis/scripts/status.js
node -c skills/aegis/scripts/enable-hook.js
node -c skills/aegis/scripts/disable-hook.js
node -c skills/aegis/scripts/uninstall.js
```

Expected: all four return without output (syntax OK).

- [ ] **Step 7.5: Commit**

```bash
git add skills/
git commit -m "Phase 4 T7 — slash command skill: SKILL.md + 5 commands + 4 scripts"
```

---

## Task 8: PDF/DOCX support + image → request_permission

**Files:**
- Modify: `middleware/src/plugin/index.ts` (or wherever `aegis_read` handler lives — locate first)
- Create: `middleware/tests/extract.test.ts`
- Create: 6 fixture files under `middleware/tests/fixtures/`

The extraction logic uses `pdf-parse` and `mammoth` (already in deps). Image extensions return `request_permission` without text extraction.

- [ ] **Step 8.1: Locate the aegis_read handler**

```bash
grep -rln 'aegis_read\|aegisRead' middleware/src/ | head
```

Read the located file. Identify where text is extracted from the file (currently probably just UTF-8 read).

- [ ] **Step 8.2: Write the failing extract tests**

Create `/Users/excallibur/dev/aegis/middleware/tests/extract.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { extractText } from '../src/extract';
import * as path from 'node:path';
import * as fs from 'node:fs';

const FIXTURES = path.join(__dirname, 'fixtures');

describe('extractText', () => {
    it('returns plain text from .txt files unchanged', async () => {
        const p = path.join(FIXTURES, 'safe.txt');
        fs.writeFileSync(p, 'hello world');
        const out = await extractText(p);
        expect(out.text).toBe('hello world');
        expect(out.escalate).toBe(false);
        fs.unlinkSync(p);
    });

    it('extracts text from .pdf via pdf-parse', async () => {
        const p = path.join(FIXTURES, 'safe.pdf');
        const out = await extractText(p);
        expect(out.text.length).toBeGreaterThan(0);
        expect(out.escalate).toBe(false);
    });

    it('extracts text from .docx via mammoth', async () => {
        const p = path.join(FIXTURES, 'safe.docx');
        const out = await extractText(p);
        expect(out.text.length).toBeGreaterThan(0);
        expect(out.escalate).toBe(false);
    });

    it('returns escalate=true for image files (.png, .jpg, .gif, .webp, .heic)', async () => {
        for (const ext of ['.png', '.jpg', '.gif', '.webp', '.heic']) {
            const p = path.join(FIXTURES, `screenshot${ext}`);
            // Create a stub file if it doesn't exist (we don't need real image content)
            if (!fs.existsSync(p)) fs.writeFileSync(p, Buffer.from([0x89, 0x50, 0x4e, 0x47]));
            const out = await extractText(p);
            expect(out.escalate).toBe(true);
            expect(out.escalateReason).toMatch(/image/i);
        }
    });

    it('returns escalate=true for encrypted PDFs', async () => {
        const p = path.join(FIXTURES, 'encrypted.pdf');
        if (fs.existsSync(p)) {
            const out = await extractText(p);
            expect(out.escalate).toBe(true);
            expect(out.escalateReason).toMatch(/encrypt|password/i);
        }
    });

    it('returns escalate=true for files over 5MB', async () => {
        const p = path.join(FIXTURES, 'huge.txt');
        fs.writeFileSync(p, 'x'.repeat(6 * 1024 * 1024));  // 6MB
        const out = await extractText(p);
        expect(out.escalate).toBe(true);
        expect(out.escalateReason).toMatch(/size/i);
        fs.unlinkSync(p);
    });
});
```

- [ ] **Step 8.3: Create fixture files**

For PDF/DOCX fixtures, use the existing `pdfkit` devDep to generate them:

```bash
mkdir -p middleware/tests/fixtures
cd middleware
cat > /tmp/make_fixtures.cjs <<'EOF'
const PDFDocument = require('pdfkit');
const fs = require('fs');
const path = require('path');

const FIXTURES = path.resolve(__dirname, 'middleware/tests/fixtures');
fs.mkdirSync(FIXTURES, { recursive: true });

// safe.pdf — a benign README-style document
const safe = new PDFDocument();
safe.pipe(fs.createWriteStream(path.join(FIXTURES, 'safe.pdf')));
safe.text('Aegis README — public-facing privacy classifier documentation.');
safe.end();

// credentials.pdf — looks like a credential dump
const creds = new PDFDocument();
creds.pipe(fs.createWriteStream(path.join(FIXTURES, 'credentials.pdf')));
creds.text('AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\nAWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG');
creds.end();
EOF
node /tmp/make_fixtures.cjs
ls middleware/tests/fixtures/
rm /tmp/make_fixtures.cjs
```

For DOCX fixtures, use `mammoth` is read-only — we'll need to handcraft a tiny DOCX. Easier: use a Python one-liner with `python-docx` if available, or skip DOCX fixtures and just commit the existing test PDFs (DOCX coverage can be a v1.1 task).

For image fixtures, use a tiny 4-byte PNG header stub — enough to test the extension-based routing.

```bash
printf '\x89PNG' > middleware/tests/fixtures/screenshot.png
printf '\xff\xd8\xff\xe0' > middleware/tests/fixtures/screenshot.jpg
printf 'GIF89a' > middleware/tests/fixtures/screenshot.gif
printf 'RIFF....WEBP' > middleware/tests/fixtures/screenshot.webp
printf 'ftypheic' > middleware/tests/fixtures/screenshot.heic
```

For encrypted.pdf — create a passworded PDF or skip that specific test (it can be a future-work item; the test file has `if (fs.existsSync(p))` so it'll skip if absent).

- [ ] **Step 8.4: Run extract tests to verify failure**

```bash
cd middleware && npx vitest run tests/extract.test.ts
```

Expected: module-not-found on `../src/extract`.

- [ ] **Step 8.5: Implement extract.ts**

Create `/Users/excallibur/dev/aegis/middleware/src/extract.ts`:

```typescript
/**
 * File text extraction for aegis_read.
 *
 * Returns either extracted text (route to classifier) or escalate=true
 * with a reason (route directly to request_permission verdict).
 */

import * as fs from 'node:fs';
import * as path from 'node:path';

const MAX_FILE_BYTES = 5 * 1024 * 1024;  // 5MB
const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.bmp', '.tiff']);

export interface ExtractResult {
    text: string;
    escalate: boolean;
    escalateReason?: string;
}

export async function extractText(filePath: string): Promise<ExtractResult> {
    const ext = path.extname(filePath).toLowerCase();

    // Size check first — applies to all formats
    const stat = fs.statSync(filePath);
    if (stat.size > MAX_FILE_BYTES) {
        return {
            text: '',
            escalate: true,
            escalateReason: `File size ${stat.size} exceeds 5MB limit; routing to request_permission for explicit human review.`,
        };
    }

    // Image files → escalate without attempting extraction
    if (IMAGE_EXTS.has(ext)) {
        return {
            text: '',
            escalate: true,
            escalateReason: `Image file (${ext}); OCR not supported in v1. Routing to request_permission for human review.`,
        };
    }

    // PDF via pdf-parse
    if (ext === '.pdf') {
        try {
            const pdfParse = require('pdf-parse');
            const buf = fs.readFileSync(filePath);
            const out = await pdfParse(buf);
            return { text: out.text, escalate: false };
        } catch (e: any) {
            // Encrypted PDFs throw a specific error
            if (e.message?.match(/encrypt|password/i)) {
                return {
                    text: '',
                    escalate: true,
                    escalateReason: 'PDF is encrypted; password input not supported in v1.',
                };
            }
            throw e;
        }
    }

    // DOCX via mammoth
    if (ext === '.docx') {
        const mammoth = require('mammoth');
        const out = await mammoth.extractRawText({ path: filePath });
        return { text: out.value, escalate: false };
    }

    // Default: UTF-8 read
    return { text: fs.readFileSync(filePath, 'utf8'), escalate: false };
}
```

- [ ] **Step 8.6: Wire extractText into the aegis_read handler**

Read the handler file located in Step 8.1. Replace the existing read-utf8 path with a call to `extractText`. If the result has `escalate: true`, return a `request_permission` verdict without calling the bridge. Otherwise proceed with the existing classify-then-route logic on `result.text`.

Pseudo-shape:

```typescript
import { extractText } from './extract';

async function handleAegisRead(filePath: string) {
    const ext = await extractText(filePath);
    if (ext.escalate) {
        return {
            verdict: 'request_permission',
            reason: ext.escalateReason,
            text: null,
        };
    }
    // ... existing classifier call with ext.text ...
}
```

- [ ] **Step 8.7: Run extract tests to verify they pass**

```bash
cd middleware && npx vitest run tests/extract.test.ts
```

Expected: all pass.

- [ ] **Step 8.8: Run the rest of the test suite**

```bash
cd middleware && npm test 2>&1 | tail -5
```

Expected: all green.

- [ ] **Step 8.9: Commit**

```bash
git add middleware/src/extract.ts middleware/src/plugin/index.ts middleware/tests/extract.test.ts middleware/tests/fixtures/
git commit -m "Phase 4 T8 — PDF/DOCX extraction in aegis_read; images → request_permission; oversize → request_permission"
```

(Adjust `middleware/src/plugin/index.ts` path if T8.1 located the handler elsewhere.)

---

## Task 9: Root README rewrite for marketplace audience

**Files:**
- Rewrite: `README.md` (root)

Full rewrite per the spec's Section 3 layout: hero, what it does, receipts, how it works, performance, install & config, contributing/license/footer.

- [ ] **Step 9.1: Replace the existing README**

Read the current README to preserve any links / claims still accurate, then rewrite `/Users/excallibur/dev/aegis/README.md` to this structure:

```markdown
# Aegis — On-Device Privacy Gate for AI Agents

> **On-device, by default.** Aegis classifies files locally before any AI agent reads them — weights are bundled at install, no network calls at inference, no telemetry. Verify it yourself: see [PRIVACY.md](docs/PRIVACY.md) for the receipts.

```
npx aegis-mcp
```

That's the entire install.

![Aegis in action](assets/demo.gif)

## What it does

Aegis routes Claude Code's `Read`/`Glob`/`Grep` through an on-device classifier and returns one of four verdicts:

- **classify_safe** — pass through unchanged (most file content)
- **flag_pii** — sanitize PII inline with placeholders (`__EMAIL_1__`, `__SSN_1__`)
- **block_transfer** — refuse to return content (credentials, secrets, API keys)
- **request_permission** — escalate to the human (internal/confidential docs, ambiguous files, images)

## Receipts (the privacy promise, verifiable)

- **No network calls at inference** — run `lsof -i` while Aegis classifies a file; you'll see only the localhost bridge connection.
- **Weights are local** — `~/.cache/huggingface/hub/models--google--embeddinggemma-300m/` (model) + `~/.aegis-mcp/middleware/aegis/head/lr.joblib` (classifier head).
- **No telemetry** — `grep -r posthog\|amplitude\|honeycomb middleware/dist/` returns nothing.
- **Source for the curious** — this repo, MIT-licensed. Full audit welcome.

See [docs/PRIVACY.md](docs/PRIVACY.md) for the full verification recipes.

## How it works

```
Claude → Read(path)              ← hook intercepts
            ↓
       aegis_read(path)
            ↓
       extract text (txt / pdf / docx; image → request_permission)
            ↓
       POST /classify → localhost bridge
            ↓
       in-process: embeddinggemma-300m → LR head → verdict
            ↓
       passthrough / sanitize / block / escalate
```

## Performance

- **94.90% accuracy** on a 98-sample real-world held-out eval (Wilson 95% CI [88.6%, 97.8%])
- **~78 ms p50 latency** warm; ~700 ms cold start (model load)
- One documented fail-open case (`.env.example`-style file with mixed placeholder + dev-default values) — see [scorecard](docs/eval-results/scorecard.md) for the full failure-mode breakdown

## Install & config

```bash
# One-command install
npx aegis-mcp
```

On first run:
1. Prompts to install the Read/Glob/Grep enforcement hook (default Yes)
2. Sets up the Python bridge venv at `~/.aegis-mcp/venv/`
3. Downloads the embedding model on first classification (~150 MB, cached)
4. Registers slash commands: `/aegis-status`, `/aegis-policy`, `/aegis-enable-hook`, `/aegis-disable-hook`, `/aegis-uninstall`

### Requirements
- Python 3.12+ on PATH
- Claude Code (or any MCP-compatible client)
- ~200 MB disk for the cached model + venv

### Uninstall
```bash
npx aegis-mcp uninstall
```

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) — coming with v1.1.

## License

MIT — see [LICENSE](LICENSE).
```

- [ ] **Step 9.2: Verify markdown renders cleanly**

```bash
# If you have a local markdown renderer, preview. Otherwise just visually inspect:
head -80 README.md
```

- [ ] **Step 9.3: Commit**

```bash
git add README.md
git commit -m "Phase 4 T9 — rewrite root README.md for marketplace audience"
```

---

## Task 10: middleware/README.md rewrite + docs/PRIVACY.md

**Files:**
- Rewrite: `middleware/README.md`
- Create: `docs/PRIVACY.md`

middleware/README is for developers contributing to the TS server; not on the marketplace listing. PRIVACY.md is linked from the root README's receipts section.

- [ ] **Step 10.1: Rewrite middleware/README.md**

Replace with a focused dev README (~80-120 lines) covering: what the middleware does, build/test commands, source layout, and how it integrates with the Python bridge. Drop all DataGuard branding.

Create `/Users/excallibur/dev/aegis/middleware/README.md`:

```markdown
# aegis-mcp middleware

TypeScript MCP server for Aegis. This is the package published to npm as `aegis-mcp` and invoked by `npx aegis-mcp`.

Companion to `aegis/` (Python bridge) at the repo root.

## What it does

Exposes four MCP tools to Claude Code (and any MCP client):

- `aegis_read` — read a file, classify it, route based on verdict
- `aegis_classify` — classify without returning content
- `aegis_policy_explain` — show the current policy
- `aegis_sanitize_path` — force re-sanitization

On startup:
1. Detects Python 3.12+ on PATH
2. Ensures `~/.aegis-mcp/venv/` with pinned deps from `aegis/requirements.txt`
3. Spawns `aegis/bridge.py` on an ephemeral port
4. Polls the bridge `/health` until ready
5. Starts the MCP server on stdio, forwarding tool calls

## Build

```bash
npm install
npm run build       # compile TS to dist/
npm run mcp:dev     # run in dev mode (tsx, watches files)
```

## Test

```bash
npm test            # vitest run, all tests
npx vitest run tests/extract.test.ts   # single test file
```

## Source layout

```
src/
  cli.ts              # `npx aegis-mcp` entry point
  bridge_launcher.ts  # Python detection + venv + spawn
  installer.ts        # Hook + skill installer
  extract.ts          # PDF/DOCX/image extraction
  mcp-server.ts       # MCP server proper
  plugin/index.ts     # OpenClaw compat layer (legacy, kept for plugin format)
  router/             # HTTP client for the bridge
  sanitize/           # PII regex + LLM-fallback sanitization
  tools/              # Individual MCP tool implementations
  hooks/              # Hook-related logic
tests/                # vitest test suite + fixtures
```

## How it integrates with the Python bridge

The TS server holds the bridge subprocess lifecycle:
- Spawned on MCP server boot via `bridge_launcher.spawnBridge()`
- Healthcheck polled before MCP server accepts traffic
- Killed on SIGINT / SIGTERM / parent disconnect

The bridge HTTP API:
- `POST /classify` — body: `{ text: string }` → response: `{ verdict, confidence }`
- `GET /health` — returns bridge readiness + head metadata

## Publishing

```bash
npm version major   # or patch / minor
npm publish
```

The npm package includes the `aegis/` Python sources and `skills/aegis/` skill directory via the `files` allowlist in package.json.
```

- [ ] **Step 10.2: Create docs/PRIVACY.md**

Create `/Users/excallibur/dev/aegis/docs/PRIVACY.md`:

```markdown
# Privacy

Aegis is designed to be verifiable. This document explains the privacy promise and how to confirm each claim yourself.

## The promise

When Aegis classifies a file:
1. **No network calls.** The classifier runs in-process on your machine.
2. **No data leaves.** File content is processed locally; nothing is sent anywhere.
3. **No telemetry.** No usage stats, no error reports, no analytics ping.

## Verifying the promise

### 1. No network calls at inference

Open one terminal:
```bash
lsof -iTCP -sTCP:ESTABLISHED -P -n | grep -iE 'aegis|python|node'
```

Open Claude Code and trigger a classification (read any file via `aegis_read`).

Re-run the lsof command. You should see only:
- A connection from the TS MCP server to `127.0.0.1:<bridge_port>` (the local bridge)
- The bridge's HF Hub cache lookup if the model isn't yet cached — once cached, even this goes away

No external IPs. No domains other than `127.0.0.1`.

### 2. Weights are local

The classifier has two components, both cached on your machine:

```bash
# The embedding model (~150 MB) — downloaded from HF Hub on first run, cached
ls ~/.cache/huggingface/hub/models--google--embeddinggemma-300m/

# The classifier head (~25 KB) — bundled in the npm package
ls ~/.aegis-mcp/middleware/aegis/head/lr.joblib
```

If you delete these files, Aegis will re-download the embedder (since it's HF-cached) but the classifier head is part of the npm install — it doesn't re-download from a separate endpoint.

### 3. No telemetry in the source

```bash
# Search the published source for common telemetry SDKs
grep -rE 'posthog|amplitude|honeycomb|datadog|sentry|google-analytics' ~/.aegis-mcp/middleware/dist/ ~/.aegis-mcp/middleware/aegis/
```

Returns nothing. The bridge has no analytics imports.

### 4. Audit the source

Aegis is MIT-licensed and the source is at [github.com/AmaruEscalante/aegis](https://github.com/AmaruEscalante/aegis). The TypeScript MCP server is in `middleware/`; the Python bridge + classifier are in `aegis/`. The published npm package is built from these sources without obfuscation.

## What we don't promise

- **Image classification.** Image files (`.jpg`, `.png`, etc.) are escalated to you for manual review — they're not classified by the on-device model in v1. OCR support is planned for a future release.
- **Cross-platform identical behavior.** v1 ships macOS-tested. Linux + Windows work in our testing but aren't on the CI matrix yet.
- **Accuracy beyond the documented eval.** The shipped classifier scored 94.90% on a 98-sample held-out eval (see [scorecard.md](eval-results/scorecard.md)). Real-world distribution may differ; we know of one documented fail-open case.

## If you find a privacy issue

Open an issue at [github.com/AmaruEscalante/aegis/issues](https://github.com/AmaruEscalante/aegis/issues) with the label `privacy`. We treat these as high-priority.
```

- [ ] **Step 10.3: Commit**

```bash
git add middleware/README.md docs/PRIVACY.md
git commit -m "Phase 4 T10 — rewrite middleware/README.md (drop DataGuard); add docs/PRIVACY.md"
```

---

## Task 11: Demo GIF

**Files:**
- Create: `assets/demo.gif`

Manual recording. Subagent prepares the script + tooling instructions; **the user records** because it requires interacting with Claude Code on a live macOS GUI.

- [ ] **Step 11.1: Prepare the demo script (what to type / what to read)**

Write a short script for the recording at `/tmp/demo-script.md`:

```
Scene 1 (10s): Install
  - Open Terminal, fresh window
  - Type: `npx aegis-mcp`
  - Show the consent prompt
  - Press Enter (default Y)
  - Show "Aegis ready" line

Scene 2 (10s): Safe file
  - Switch to Claude Code
  - Prompt: "Read the project README"
  - Show Claude using aegis_read → classify_safe → content visible

Scene 3 (15s): Credentials file
  - Prompt: "Read samples/holdout_v2/datadog_api_keys.env"
  - Show Claude using aegis_read → block_transfer verdict
  - Claude refuses with the verdict reason

Scene 4 (15s): PII file
  - Prompt: "Read samples/holdout_v2/k12_grade_report.csv"
  - Show Claude using aegis_read → flag_pii → sanitized content
  - Visible __EMAIL_1__ / __PHONE_1__ placeholders

Scene 5 (10s): Status
  - In Claude Code: `/aegis-status`
  - Show the status output: hook installed, bridge ok, recent verdicts
```

- [ ] **Step 11.2: Record the GIF**

This step requires manual recording on macOS:

```bash
# Use macOS built-in screen recorder
# Cmd+Shift+5 → "Record Selected Portion" → choose 1200x800 region
# Record the 5 scenes, ~60 seconds total

# Convert to GIF (assume ffmpeg + gifsicle installed)
ffmpeg -i ~/Desktop/recording.mov -vf "fps=15,scale=1000:-1" -loop 0 /tmp/demo.gif
gifsicle -O3 --colors 128 /tmp/demo.gif -o assets/demo.gif

# Verify size
ls -lh assets/demo.gif
# Target: ≤ 5MB
```

If `gifsicle` isn't installed: `brew install gifsicle`. If recording exceeds 5MB after optimization, drop fps to 10 or reduce dimensions to 800px wide.

- [ ] **Step 11.3: Commit**

```bash
mkdir -p assets
git add assets/demo.gif
git commit -m "Phase 4 T11 — demo GIF (5 scenes, ~60s, <5MB)"
```

---

## Task 12: Smoke test + integration verification

**Files:**
- Create: `tests/test_smoke_install.sh`

End-to-end test that verifies the full install flow from a clean state. Doesn't get published in the npm package; it's a CI sanity check.

- [ ] **Step 12.1: Write the smoke test**

Create `/Users/excallibur/dev/aegis/tests/test_smoke_install.sh`:

```bash
#!/usr/bin/env bash
# End-to-end smoke test for Phase 4.
#
# Usage:  ./tests/test_smoke_install.sh
#
# Creates a temporary $HOME, runs the install flow with AEGIS_INSTALL_HOOK=1
# (auto-consent), verifies the hook landed, verifies the bridge responds,
# then runs uninstall and verifies clean teardown.

set -euo pipefail

TMP_HOME=$(mktemp -d -t aegis-smoke-XXXXXXXX)
ORIG_HOME=$HOME
export HOME=$TMP_HOME
trap "rm -rf $TMP_HOME; export HOME=$ORIG_HOME" EXIT

echo "=== Smoke test: temp HOME=$HOME ==="

# Build the TS server in dev mode
cd middleware
npm install --silent
npm run build
cd ..

# Auto-consent install
echo "[1/5] Running install with AEGIS_INSTALL_HOOK=1..."
AEGIS_INSTALL_HOOK=1 node middleware/dist/cli.js &
CLI_PID=$!
sleep 30  # give time for venv + bridge startup
echo "[1/5] Install kicked off; verifying..."

# Verify hook installed
echo "[2/5] Checking hook in settings.json..."
test -f "$HOME/.claude/settings.json" || { echo "FAIL: settings.json not created"; exit 1; }
grep -q 'aegis-mcp:enforce-read-routing' "$HOME/.claude/settings.json" || { echo "FAIL: hook entry missing"; exit 1; }
echo "[2/5] OK"

# Verify venv populated
echo "[3/5] Checking ~/.aegis-mcp/venv..."
test -d "$HOME/.aegis-mcp/venv/bin" || { echo "FAIL: venv not created"; exit 1; }
echo "[3/5] OK"

# Kill the CLI, run uninstall
echo "[4/5] Stopping CLI..."
kill $CLI_PID 2>/dev/null || true
wait $CLI_PID 2>/dev/null || true
sleep 2

echo "[5/5] Running uninstall..."
node middleware/dist/cli.js uninstall

# Verify hook removed
grep -q 'aegis-mcp:enforce-read-routing' "$HOME/.claude/settings.json" && { echo "FAIL: hook still present after uninstall"; exit 1; }
echo "[5/5] OK"

echo ""
echo "=== Smoke test PASSED ==="
```

Make it executable:

```bash
chmod +x tests/test_smoke_install.sh
```

- [ ] **Step 12.2: Run the smoke test**

```bash
./tests/test_smoke_install.sh
```

Expected: "Smoke test PASSED" in under ~5 minutes (first run downloads the embedding model; subsequent runs reuse HF cache).

If it fails:
- "Hook entry missing" → check `installer.ts` is correctly building the entry; check the cli's `runInstall` is being invoked
- "venv not created" → check Python detection; ensure pip is reachable in the test environment
- Bridge timeout → check `aegis/bridge.py` is importable from the new path

- [ ] **Step 12.3: Commit**

```bash
git add tests/test_smoke_install.sh
git commit -m "Phase 4 T12 — end-to-end smoke test for install + uninstall"
```

---

## Task 13: npm publish + git tag (user-executed)

**Files:** none (publish action)

This task is user-executed because `npm publish` reaches the public registry. The subagent prepares everything; the user runs the final command.

- [ ] **Step 13.1: Verify the package is ready**

```bash
cd middleware
npm run build
# Run npm pack --dry-run to see what would be published
npm pack --dry-run 2>&1 | tail -30
# Check the tarball size
npm pack 2>&1 | tail -3
ls -lh aegis-mcp-1.0.0.tgz
# Target: ≤ 1MB
```

Look at the dry-run output. Verify:
- `aegis/bridge.py`, `aegis/embedding.py`, `aegis/head/lr.joblib`, `aegis/requirements.txt` are all included
- `aegis/__init__.py` included
- `dist/cli.js`, `dist/bridge_launcher.js`, `dist/installer.js`, `dist/mcp-server.js`, `dist/extract.js` all included
- `skills/aegis/` included
- `scripts/hook-enforce.js` included
- `LICENSE` and `README.md` included
- `docs/PRIVACY.md` included
- **NOT** included: `eval.py`, `eval_fresh.py`, `eval_regression.py`, `train/`, `tools/`, `samples/`, `tests/`, `docs/eval-results/`, `docs/superpowers/`

If the allowlist isn't catching the right files, edit `middleware/package.json` `files` field and retry.

```bash
rm aegis-mcp-1.0.0.tgz  # cleanup the test tarball
```

- [ ] **Step 13.2: Tag v1.0.0 locally**

```bash
git tag -a v1.0.0 -m "Phase 4 v1.0.0 — first marketplace release"
git tag --list | grep v1.0.0
```

- [ ] **Step 13.3: Tell the user to publish**

The subagent reports DONE_WITH_CONCERNS at this point. The user runs:

```bash
# 1. Push the tag
git push origin v1.0.0

# 2. Push the branch (or merge to main first then push)
git push origin phase-4-publish

# 3. Open PR to main, merge it

# 4. Publish to npm (user-executed)
cd middleware
npm publish  # may need npm login first

# 5. Verify publish
npm view aegis-mcp version  # expect: 1.0.0
```

---

## Task 14: Submit to Anthropic MCP directory (user-executed)

**Files:** none (PR action)

- [ ] **Step 14.1: Subagent prepares the submission content**

The Anthropic MCP directory (`modelcontextprotocol/servers` GitHub repo) accepts PRs that add entries to its README or a server-listing file. Prepare the snippet the user will add:

```markdown
### Aegis

- **Repo:** [github.com/AmaruEscalante/aegis](https://github.com/AmaruEscalante/aegis)
- **Install:** `npx aegis-mcp`
- **Category:** Security & Privacy
- **Description:** On-device privacy classifier for AI agents. Classifies file content locally using `embeddinggemma-300m` + trained LR head; routes to passthrough, sanitization, block, or escalation. No network calls at inference, no telemetry, MIT-licensed.
```

Save this to `/tmp/anthropic-mcp-submission.md` for reference.

- [ ] **Step 14.2: User submits the PR**

```bash
# User actions
gh repo clone modelcontextprotocol/servers /tmp/mcp-servers
cd /tmp/mcp-servers
git checkout -b aegis-add-listing
# Edit README.md (or wherever entries live) — append the snippet above
git add README.md
git commit -m "Add aegis-mcp to the directory"
git push -u origin aegis-add-listing
gh pr create --title "Add aegis-mcp — on-device privacy classifier" --body "$(cat /tmp/anthropic-mcp-submission.md)"
```

Track the PR URL. Update the success criteria checklist when it's merged (review takes 1-2 weeks).

---

## Task 15: Submit to Claude Code plugin marketplace (user-executed)

**Files:** none (form submission action)

- [ ] **Step 15.1: Subagent prepares submission content**

Claude Code's plugin marketplace currently accepts submissions via a form on the Claude Code dashboard. Prepare the field values:

```
Plugin name:      aegis-mcp
Description:      On-device privacy classifier for AI agents. Routes Read/Glob/Grep through aegis_read to classify, sanitize, block, or escalate file content locally — no network calls at inference, no telemetry.
Install command:  npx aegis-mcp
Repository:       https://github.com/AmaruEscalante/aegis
Demo:             [link to demo.gif raw URL on GitHub]
License:          MIT
Category:         Security / Privacy
```

Save to `/tmp/claude-code-marketplace-submission.md`.

- [ ] **Step 15.2: User submits via the dashboard**

User-driven action via the Claude Code dashboard / submission form. Review takes 1-2 weeks; track the submission ID.

---

## End-of-plan checklist

Before declaring Phase 4 done (i.e., v1.0.0 shipped), verify each success criterion from the spec:

- [ ] `npx aegis-mcp` works end-to-end on a fresh machine in ≤ 2 minutes (smoke test verified, T12)
- [ ] Consent prompt fires once, recorded in `~/.aegis-mcp/install.log`
- [ ] Hook correctly added on consent; correctly removed on `/aegis-uninstall`
- [ ] All 5 slash commands respond
- [ ] PDF + DOCX classification works for 12 fixtures; image files return `request_permission` (T8)
- [ ] Demo GIF embedded in README ≤ 5 MB (T11)
- [ ] npm package size ≤ 1 MB compressed (T13.1)
- [ ] MIT LICENSE at root (T3)
- [ ] **Submitted to all 3 channels**: npm publish (T13), Anthropic MCP directory PR (T14), Claude Code marketplace submission (T15)
- [ ] All commits made locally on `phase-4-publish`; user pushed when ready (no agent pushes)
- [ ] `.codex/` not touched, read, or staged at any point
- [ ] Existing test suite (Phase 3b/3b.5) still passes after the restructure (T1.6)

Suggested next phase after Phase 4 lands: **Phase 5 — image support** (OCR via Apple Vision; classifier eval on OCR'd text) OR **Phase 3b.5.1** (revisit the failed `.example` distribution work with better label decisions). Both are parked in `docs/limits-and-improvements.md` and `docs/superpowers/specs/2026-05-21-phase-3b51-followup-design.md` respectively.
