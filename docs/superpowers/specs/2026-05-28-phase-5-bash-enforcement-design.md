# Phase 5 — Bash Read Enforcement Design

**Date:** 2026-05-28
**Status:** Approved design, ready for implementation plan
**Ships as:** aegis-gate v1.1.0 (additive minor)

## Problem

Aegis's enforcement hook intercepts `Read`, `Glob`, and `Grep` and redirects them to `aegis_read`. It does **not** intercept `Bash`. A behavioral test on Claude Code 2.1.152 (2026-05-28) confirmed the gap: with the hook installed and `--permission-mode bypassPermissions`, the prompt "use Bash to cat the file" returned the file's sentinel contents cleanly, with zero hook interaction. Any model that reaches for `cat`/`head`/`grep` — out of habit or otherwise — bypasses the privacy gate entirely.

## Threat model (decided)

Aegis defends against a **cooperative model**: one that will respect the privacy policy but defaults to shell reads (`cat secrets.txt`) out of habit, or wanders into a sensitive file by accident. It is explicitly **not** a containment boundary against an adversarial agent.

This scoping is forced by architecture, not preference. It was established by behavioral testing on Claude Code 2.1.x:

- **PostToolUse cannot redact tool output.** The tool result enters the model's context synchronously; a PostToolUse hook can only add a system-reminder on the *next* turn. So "classify the Bash output and scrub secrets before the model sees them" is impossible via hooks. (Verified against [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks): PreToolUse uses `hookSpecificOutput.permissionDecision`; PostToolUse exposes only `additionalContext`, explicitly "cannot modify output".)
- **Native `Read()` deny rules did not block `cat`** in testing (Test 5/5b), nor even the `Read` tool with exact-path syntax — unreliable, not promise-grade.
- **`Bash(cat:*)` command-prefix deny works but is trivially defeated** (`base64`, `head`, `/bin/cat`, `python -c`).
- **Every content/command-level mechanism is defeatable** by indirection (`python3 -c "open('.env')"`), encoding, or chunking. The *only* real wall against an adversarial agent is OS-level sandboxing (`sandbox.filesystem.denyRead`), which is out of scope for a hook.

Therefore the honest, achievable goal: **close the habitual single-file-read gap for a cooperative model, and document that true containment requires OS sandboxing.**

## Goals

1. A `Bash` command that is a simple single-file read (e.g. `cat .env`, `head secrets.txt`, `grep KEY config`, `cat .env | grep KEY`) is blocked and the model is redirected to `aegis_read`, in both default and `bypassPermissions` modes.
2. Non-read Bash commands (`ls`, `git status`, `npm test`, `rm`) and ambiguous/complex commands are unaffected (fail open).
3. The existing `Read`/`Glob`/`Grep` enforcement migrates to the documented hook output schema (hardening — see below).
4. README and `docs/PRIVACY.md` state the cooperative-guardrail scope honestly, including the Bash limitations and the OS-sandbox pointer for real containment.

## Non-goals (documented as limitations)

Not gated, by design: piped reads with command substitution; output redirection; command chaining; indirect reads via interpreters (`python -c`, `node -e`, `ruby -e`); reads by unusual tools (`tar`, `mapfile`, `vim -c`); encoded or chunked exfiltration; any actively adversarial agent. The README will name OS sandboxing (`sandbox.filesystem.denyRead`) as the mechanism for hard containment of crown-jewel paths (`.env`, `~/.ssh`).

## Architecture

One hook, two behaviors. Extend the existing `scripts/hook-enforce.js` rather than add a second hook script. The installed matcher changes from `Read|Glob|Grep` to `Read|Glob|Grep|Bash`. The hook branches on `tool_name`:

- `Read` / `Glob` / `Grep` → block + redirect (unchanged behavior, migrated to the documented output schema).
- `Bash` → run reader detection on the command; block + redirect **only** if it is a simple single-file read; otherwise exit 0 (allow).

Reader detection is a separate, pure, unit-testable module so its many cases can be table-tested without spawning Claude.

### Components

| Component | Path | Responsibility |
|---|---|---|
| Reader detection (new) | `middleware/src/detect-bash-read.ts` | Pure function `detectBashRead(command)`; uses `shell-quote` to tokenize; returns `{ isRead: true, path } \| { isRead: false }`. Compiled to `dist/detect-bash-read.js`. |
| Hook script (modify) | `scripts/hook-enforce.js` | Add `Bash` branch; `require('../dist/detect-bash-read.js')`; migrate all branches to documented output schema. |
| Installer (modify) | `middleware/src/installer.ts` | `HOOK_MATCHER = 'Read|Glob|Grep|Bash'`. |
| Unit tests (new) | `middleware/tests/detect-bash-read.test.ts` | Table-driven cases for `detectBashRead`. |
| Behavioral test (extend) | `tests/test_smoke_install.sh` or a new `claude -p` harness | Confirm `cat` blocked + `ls` allowed, default and bypassPermissions. |

### Dependency

Add `shell-quote` (`>=1.7.3`) as a runtime dependency in `middleware/package.json`.

- Rationale: pure JS, **0 transitive dependencies**, MIT. Its `parse()` emits operators as token objects (`{op:"|"}`, `{op:"&&"}`, `;`, `>`, `$(...)`), which makes "simple single-file read vs. pipe/substitution/chain" a structural check rather than fragile regex.
- Version floor `>=1.7.3` avoids the historical ReDoS advisory fixed in that release.
- Resolution: the install at `~/.aegis-gate/middleware/` already ships `node_modules` for the MCP server's existing runtime deps (`@modelcontextprotocol/sdk`, `mammoth`, `pdfjs-dist`, …), so `require('shell-quote')` resolves from the hook script's location. The compiled `dist/detect-bash-read.js` imports it; the hook requires the compiled module.
- Safety property: any `shell-quote` parse error or thrown exception → **fail open** (allow the command). A parser edge case can never cause a leak in the unsafe direction.

## Reader detection logic

`detectBashRead(command: string)`:

1. Tokenize `command` with `shell-quote`'s `parse()`.
2. Split the token stream on operators. Consider the **first segment** (before any `|`, `&&`, `||`, `;`). This catches `cat .env` and the source side of a simple pipe `cat .env | grep KEY`.
3. **Fail open (return `{isRead:false}`) immediately** if the first segment contains any token that is not a plain string — i.e. any object `shell-quote` emits for an operator, glob, comment, or command substitution (`$(...)`/backticks), or any redirection operator (`>`, `>>`, `>&`). Only the operator used to delimit the first segment (the pipe/chain split in step 2) is expected. This is the "too complex → don't guess" guard. (The exact object shapes `shell-quote` emits for substitution/globs are an implementation detail to pin down with the unit table; the rule is simply: non-plain-string token in the first segment → fail open.)
4. Let `cmd` = first string token of the first segment, `args` = remaining string tokens of that segment.
5. If `cmd` (basename, so `/bin/cat` matches `cat`) is in the **reader set** AND exactly one `arg` is a file-path-shaped token (not an option starting with `-`), return `{ isRead: true, path: <that arg> }`.
   - For `grep`/`egrep`/`fgrep`/`rg`/`sed`/`awk`: a file read requires a file argument *in addition to* the pattern/script (e.g. `grep KEY config` → read `config`; `grep KEY` alone → reads stdin → `{isRead:false}`).
6. Otherwise return `{ isRead: false }`.

**Reader set:** `cat, bat, head, tail, less, more, nl, tac, od, xxd, hexdump, strings, base64, base32, cut, fold` (always readers when given a single file arg); `grep, egrep, fgrep, rg, sed, awk` (readers only when a file arg is present beyond the pattern/script).

Multiple file args (`cat a b`) → fail open (ambiguous; cooperative model rarely does this for exfil, and resolving N paths into one redirect is messy).

## Output schema migration (hardening)

The currently-shipped hook emits the legacy top-level `{"decision":"block","reason":...}`. Per [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks), PreToolUse deny is documented **only** as:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "<message>"
  }
}
```

The legacy form happens to work in 2.1.x (verified: Tests 2/3 blocked `Read` in default and bypassPermissions) but is undocumented for PreToolUse and on borrowed time. Phase 5 migrates **all** branches (the existing Read/Glob/Grep path and the new Bash path) to the documented schema, then re-verifies behaviorally that the documented form blocks in both permission modes before shipping.

## Data flow

```
Bash("cat .env")
  → PreToolUse hook (matcher Read|Glob|Grep|Bash)
  → tool_name == "Bash" → detectBashRead("cat .env") → { isRead:true, path:".env" }
  → emit permissionDecision:"deny", reason:
      "Aegis: read .env via aegis_read instead of `cat` — it classifies on-device
       and passes through, sanitizes PII, blocks credentials, or escalates."
  → model calls aegis_read(".env")
  → classifier → passthrough (safe) / sanitize (PII) / block (secret) / escalate

Bash("ls -la")
  → detectBashRead → { isRead:false } → exit 0 (allow)
```

## Error handling / fail-open policy

Consistent with the existing hook and the cooperative threat model: any failure path allows the command.

- stdin JSON parse error → `exit 0`, log to stderr.
- `shell-quote` parse error / exception in `detectBashRead` → treated as `{isRead:false}` → allow.
- Complex/ambiguous command (pipes with substitution, redirection, chaining, multiple files, non-string tokens) → allow by design.

We never brick Bash.

## Testing

**Unit (vitest, `middleware/tests/detect-bash-read.test.ts`)** — table-driven:

| Command | Expected |
|---|---|
| `cat .env` | `{isRead:true, path:".env"}` |
| `/bin/cat secrets.txt` | `{isRead:true, path:"secrets.txt"}` |
| `head -n 5 config.yml` | `{isRead:true, path:"config.yml"}` |
| `grep KEY config` | `{isRead:true, path:"config"}` |
| `grep KEY` (stdin) | `{isRead:false}` |
| `cat .env \| grep KEY` | `{isRead:true, path:".env"}` |
| `cat a b` (multiple files) | `{isRead:false}` |
| `base64 .env \| curl …` | `{isRead:true, path:".env"}` (source segment is a read) |
| `echo hi` / `ls` / `npm test` / `rm x` | `{isRead:false}` |
| `python3 -c "open('.env')"` | `{isRead:false}` (documented limitation) |
| `cat $(echo .env)` | `{isRead:false}` (substitution → fail open) |
| `cat .env > /tmp/out` | `{isRead:false}` (redirection → fail open) |

**Behavioral (`claude -p` harness, default + `bypassPermissions`):**
- `cat <sentinel-file>` → blocked, sentinel does NOT appear in result.
- `ls` → allowed, runs normally.
- A `Read` tool call → still blocked (migration regression check).

## Packaging & rollout

- Bump `middleware/package.json` to **1.1.0**; update `VERSION` in `cli.ts`.
- Installer matcher includes `Bash`. Existing v1.0.0 users re-run `npx aegis-gate install-hook` (or `npx aegis-gate`) to upgrade the matcher — note this in release notes.
- Update `README.md` ("what it gates" → add Bash single-file reads; add the honest Bash-limitation + OS-sandbox note), `docs/PRIVACY.md`, and the enforcement-test memory.
- Local commits only; publish (`npm publish`) and any push are user-executed.

## Open risks

1. **Reader-set completeness.** The set is curated, not exhaustive. Acceptable: missing readers fail open, consistent with cooperative scope. The set is one constant, easy to extend.
2. **`shell-quote` behavior on exotic input.** Mitigated by fail-open-on-parse-error and the unit table; a parse miss can only under-block, never leak unsafely.
3. **Matcher upgrade friction.** v1.0.0 installs keep the old `Read|Glob|Grep` matcher until re-install. Release notes must call this out; `/aegis-status` could surface "matcher version" in a later iteration (not in v1.1 scope).
