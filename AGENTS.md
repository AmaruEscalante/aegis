# AGENTS.md

Guidance for AI coding agents operating in this repository.

## Project Overview

Hackathon project ("Aegis") — a local privacy layer for agentic AI. Three sub-projects:
- **Root (Python 3.12)**: On-device FunctionGemma + cloud Gemini hybrid routing, benchmarking, and ML fine-tuning.
- **`aegis_bridge.py` (Python)**: HTTP bridge server wrapping FunctionGemma classification via Cactus or Transformers backends.
- **`middleware/` (TypeScript)**: "Aegis" OpenClaw plugin — FunctionGemma router + DataGuard sanitization engine.

## Build / Run / Test Commands

### Python (root) — managed by `uv`

```bash
# Install dependencies
uv sync

# Run the hybrid routing engine
GEMINI_API_KEY=<key> python main.py

# Run the privacy pipeline
GEMINI_API_KEY=<key> python aegis.py <file>

# Run benchmarks (custom harness, no pytest)
GEMINI_API_KEY=<key> python benchmark.py

# Submit to leaderboard
python submit.py
```

There is no formal Python test framework (no pytest/unittest). Testing is done through
`benchmark.py` (30 cases with F1 scoring), `training_files/evaluate.py`, and
`model-merge/test_cactus_model.py`.

### Aegis Bridge (`aegis_bridge.py`)

```bash
# Run with Cactus backend (default, requires converted model)
python aegis_bridge.py --backend cactus

# Run with Transformers backend (any HuggingFace model)
python aegis_bridge.py --backend transformers --model ./aegis-adapter

# Custom port
python aegis_bridge.py --backend transformers --port 7523
```

The bridge provides `POST /classify`, `POST /summarize`, and `GET /health` endpoints
on `http://127.0.0.1:7523`. The TypeScript middleware calls it over localhost.

### TypeScript (`middleware/`) — managed by `npm`

```bash
# Install dependencies
npm install                     # run from middleware/

# Build (compile TS to dist/)
npm run build                   # tsc

# Run all tests
npm test                        # vitest run

# Run a single test file
npx vitest run tests/detector.test.ts

# Run a single test by name
npx vitest run -t "detects email addresses"

# Watch mode
npm run test:watch              # vitest (interactive)

# Clean build artifacts
npm run clean                   # rm -rf dist
```

There is no ESLint, Prettier, or any linter/formatter configured. TypeScript strict
mode (`strict: true` in tsconfig.json) is the only static analysis.

## Code Style — TypeScript (`middleware/src/`)

### Imports

- **Named imports** for everything. Default imports only for Node.js built-ins (`fs`, `path`, `http`, `crypto`).
- Use `import type { ... }` for type-only imports (enforced by strict mode).
- **Ordering**: Node built-ins, external packages, internal types, internal modules.
- No barrel files — import directly from the specific module.
- Dynamic `import()` for optional/heavy dependencies (e.g., `pdf-parse`, `pdfjs-dist`).

```typescript
import fs from "fs";
import path from "path";
import { minimatch } from "minimatch";
import type { DataGuardConfig, Detection } from "../types";
import { detect, applyRedactions } from "./detector";
```

### Exports

- **Named exports** for all functions and types. No default exports except the
  single plugin entry point in `plugin/index.ts`.
- Private/internal functions are simply not exported (plain `function`).
- Tool-specific interfaces (params, results) are exported from the tool file.

### Naming

| Entity                  | Convention         | Example                              |
|-------------------------|--------------------|--------------------------------------|
| Variables, functions    | camelCase          | `auditFilePath`, `detect()`          |
| Factory functions       | `create` + Pascal  | `createDataguardRead()`              |
| Interfaces, type aliases| PascalCase         | `DataGuardConfig`, `SanitizeResult`  |
| Module-level constants  | UPPER_SNAKE_CASE   | `ENTROPY_MIN_BITS`, `BLOCKED_READ_TOOLS` |
| Serialized/JSON fields  | snake_case         | `sanitized_text`, `redaction_count`  |
| Files                   | kebab-case         | `pdf-redactor.ts`, `file-redactor.ts`|
| Directories             | lowercase          | `sanitize/`, `tools/`, `hooks/`      |
| Union literal values    | UPPER_SNAKE_CASE   | `"EMAIL"`, `"HIGH_ENTROPY"`          |

### Types

- **String literal unions** over enums (no `enum` keyword anywhere):
  ```typescript
  export type PiiCategory = "EMAIL" | "PHONE" | "SSN" | "CREDIT_CARD" | ...;
  ```
- **Interfaces** for every data shape. Shared types live in `src/types.ts` (central registry).
- **Indexed access types** to reference nested types: `SanitizeResult["method"]`.
- `any` is acceptable only at LLM/external API boundaries where types are genuinely unknown.
- Use `import type` to keep type imports separate from value imports.

### Functions

- Use `function` declarations for all named functions (not arrow functions).
- Arrow functions only for: callbacks, `.map`/`.filter`/`.sort` lambdas, event handlers.
- `async/await` for orchestration. Raw `new Promise()` only for wrapping Node callback APIs.
- Factory pattern for dependency injection — factory closes over `config`:
  ```typescript
  export function createDataguardRead(config: DataGuardConfig) {
    return async function dataguardRead(params: ...): Promise<...> { ... };
  }
  ```

### Error Handling

Follow the project's layered strategy:

1. **Policy/critical violations** — throw immediately: `throw new Error(...)`.
2. **LLM failures** — catch and degrade gracefully to regex-only. Never throw.
3. **Cache/audit failures** — silent `catch {}` (parameterless). Non-fatal; never break the tool.
4. **Tool handlers** — wrap body in try/catch, `console.error` the error, then re-throw.
5. **File extraction failures** — throw with a format-specific message.

```typescript
// Non-fatal: empty catch, no error variable
try { fs.appendFileSync(auditPath, line); } catch {}

// Fatal: throw with context
if (check.verdict === "deny") {
  throw new Error(`DataGuard denied access: ${check.reason}`);
}
```

### Comments

- **File banners**: `// ====` separator with module name and one-line description.
- **Section headers**: `// ----` separator with `Step N:` labels for pipeline flows.
- **JSDoc** on all exported functions and significant private functions.
- **Inline comments** for non-obvious logic. Mark security invariants with `// CRITICAL:`.

### File Organization

- One responsibility per file.
- `src/types.ts` is the central type registry for shared interfaces.
- `sanitize/` = domain logic, `tools/` = API layer, `hooks/` = interception, `plugin/` = composition root, `router/` = Aegis bridge client.
- No circular imports — dependencies flow: `plugin/` -> `hooks/` + `tools/` -> `router/` + `sanitize/`.

### Testing (Vitest)

- Tests in `middleware/tests/`, named `*.test.ts`.
- `import { describe, it, expect } from "vitest"`.
- Nested `describe`/`it` blocks. Test names are present-tense verb phrases:
  `"detects email addresses"`, `"preserves whitespace and formatting"`.
- Inline test data — no shared fixtures or factories.
- Test pure functions directly — no mocking, no I/O.
- Assertion style: `expect(x).toBe(y)`, `.toHaveLength()`, `.toContain()`, `.not.toContain()`.

## Code Style — Python (root)

### Imports

- `sys.path.insert(0, ...)` at top for Cactus SDK path manipulation.
- Standard library imports first (may be grouped on one line: `import json, os, time`).
- Then third-party: `from google import genai`, `from cactus import cactus_init`.
- No type annotations are used in the Python code.

### Naming

| Entity               | Convention         | Example                              |
|----------------------|--------------------|--------------------------------------|
| Functions            | snake_case         | `generate_hybrid()`, `compute_f1()`  |
| Private helpers      | `_` prefix         | `_estimate_multi_call()`, `_normalize()` |
| Constants            | UPPER_SNAKE_CASE   | `FUNCTIONGEMMA_PATH`, `PII_PATTERNS` |
| Variables            | snake_case         | `file_content`, `elapsed_ms`         |

### Error Handling

- `try/except json.JSONDecodeError` for JSON parsing with fallback defaults.
- `os.environ.get("KEY")` with warnings for missing environment variables.
- Resilient file reading: `open(file, "r", errors="replace")`.

### Documentation

- Module-level docstrings describing purpose and architecture.
- Single-line function docstrings.
- `# ---` section separators for pipeline steps.
- ANSI color constants (`GREEN`, `RED`, etc.) for CLI output formatting.

## Environment & Secrets

- **Never commit `.env` files** — verify `.gitignore` includes them.
- Use `GEMINI_API_KEY` env var for Google Gemini access.
- The `samples/` directory contains demo files with synthetic PII for testing.
- `cactus/` and `aegis-adapter/` are gitignored (large model weights).
