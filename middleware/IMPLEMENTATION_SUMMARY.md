# DataGuard Plugin — Implementation Summary

## 🎯 What Was Built

A complete, production-ready OpenClaw plugin that **intercepts all file access and forces local-only sanitization**. Raw file data never reaches the main model. All PII/secrets are replaced with safe placeholders (`__CATEGORY_n__`) that are impossible to rehydrate externally.

---

## 📁 Repository Structure

```
dataguard/
├── src/
│   ├── types.ts                    # Core TypeScript interfaces
│   ├── plugin/
│   │   └── index.ts               # Plugin entry point (register hook + tools)
│   ├── hooks/
│   │   └── before_tool_call.ts     # Blocks native file tools + egress inspection
│   ├── tools/
│   │   ├── dataguard_read.ts       # Safe file reading with auto-sanitization
│   │   ├── dataguard_search.ts     # Search with sanitized results
│   │   ├── dataguard_patch_file.ts # Permanently redact line ranges
│   │   ├── dataguard_sanitize_path.ts   # Force re-sanitization
│   │   └── dataguard_policy_explain.ts  # Policy + vault stats
│   └── sanitize/
│       ├── detector.ts             # Regex + entropy PII detection
│       ├── sanitize.ts             # Orchestrates regex + LLM sanitization
│       ├── extract.ts              # PDF/DOCX/text extraction
│       ├── policy.ts               # Path allow/deny + egress checks
│       ├── prompts.ts              # Ollama prompt templates
│       ├── cache.ts                # File-based cache (mtime + size keyed)
│       ├── vault.ts                # In-memory placeholder store
│       ├── audit.ts                # JSONL audit logging
│       └── pdf-parse.d.ts          # Type declarations
├── tests/
│   └── detector.test.ts            # Unit tests for PII detection
├── dist/                           # Compiled JavaScript (ready to deploy)
├── package.json                    # Dependencies + build scripts
├── tsconfig.json                   # TypeScript config
├── openclaw.plugin.json            # Plugin manifest for OpenClaw
├── README.md                       # Full documentation
├── QUICKSTART.md                   # 30-second setup guide
├── .gitignore                      # Git configuration
└── IMPLEMENTATION_SUMMARY.md       # This file
```

---

## 🔧 Core Modules

### `src/types.ts` (Core Types)
- `DataGuardConfig` — full plugin configuration
- `Detection` — PII/secret detection with placeholder
- `SanitizeResult` — sanitization result (text + redactions + method)
- `CacheKey` / `CacheEntry` — cache layer types
- `VaultEntry` — placeholder → original mapping
- `AuditEvent` — audit log entry
- `BeforeToolCallContext` / `BeforeToolCallResult` — OpenClaw hook types

### `src/sanitize/detector.ts` (PII Detection)
**Detects 9 categories:**
- EMAIL, PHONE, SSN, CREDIT_CARD, IBAN, SECRET, URL, IP_ADDRESS, HIGH_ENTROPY

**Features:**
- Regex patterns for structural formats (emails, SSNs, card numbers, etc.)
- Secret prefix detection (sk-, pk_, ghp_, AKIA, xox, etc.)
- Shannon entropy scoring for unknown high-entropy tokens (≥ 4.0 bits)
- Overlap prevention via "covered" set
- Deterministic offset-safe redaction application

**Key functions:**
- `detect(text)` → `Detection[]`
- `applyRedactions(text, detections)` → sanitized text

### `src/sanitize/vault.ts` (Secret Storage)
**Purpose:** Store placeholder → original mappings in-memory

**Critical security boundary:**
- `addMappings()` — add after detection
- `lookup()` — get metadata only (safe)
- `resolve()` — get original (INTERNAL USE ONLY: dataguard_patch_file only)
- Never serialized to disk, never exposed to LLM

### `src/sanitize/sanitize.ts` (Orchestration)
**Two-pass sanitization:**

1. **Pass 1 (Regex):** Detect PII via detector.ts, replace with `__CATEGORY_n__`, store in vault
2. **Pass 2 (LLM):** Send regex-redacted text to Ollama Gemma for refinement
   - If successful: merge LLM findings with regex detections
   - If timeout/error: fallback to regex-only result

**Key function:**
- `sanitize(text, config)` → `SanitizeResult { sanitized_text, redactions, method }`

### `src/sanitize/extract.ts` (File Parsing)
**Supports:**
- **Text files** — Read as UTF-8
- **PDF files** — Try `pdftotext -layout`, fallback to `pdf-parse` package
- **DOCX files** — Use `mammoth.extractRawText()`

**Key function:**
- `extractText(filePath, maxBytes)` → `{ text, format, sizeBytes }`

### `src/sanitize/policy.ts` (Path Authorization)
**Logic:**
1. Check deny globs (highest priority)
2. Check if path under allowedRoots
3. Check sanitize-always globs
4. Default: sanitize

**Also checks egress:**
- `containsSensitiveData(payload)` — blocks HTTP/curl/fetch if contains `__PLACEHOLDER_n__` or secret prefixes

**Key functions:**
- `checkPath(rawPath, config)` → `{ verdict, reason }`
- `checkFileSize(sizeBytes, config)` → boolean
- `containsSensitiveData(payload)` → `{ found, reason }`

### `src/sanitize/cache.ts` (Artifact Caching)
**Cache key:** SHA-256 of `absolutePath|mtime|size`

**Benefits:**
- Avoids re-sanitizing unchanged files
- Keyed by mtime: any write invalidates cache
- Two-level directory sharding prevents filesystem perf issues

**Key functions:**
- `get(key)` → `CacheEntry | null`
- `set(key, entry)` → void (non-fatal)

### `src/sanitize/audit.ts` (JSONL Logging)
**Logs to:** `~/.openclaw/dataguard/audit.jsonl`

**What gets logged:**
- Tool calls (dataguard_read, dataguard_search, etc.)
- Hook blocks (native file tools, egress violations)
- Redaction counts, methods used
- Path denials, policy matches

**Key function:**
- `log(event)` → void (non-fatal)

### `src/hooks/before_tool_call.ts` (Interception Hook)
**Blocks:**
1. Native file-access tools: `read`, `glob`, `grep`, `ls`, `find`, `fs.*`, etc.
   - Response: Instructive blockReason telling agent to use `dataguard_*`

2. Egress tools: `http`, `curl`, `fetch`, `exec`, `bash`, etc.
   - Check if payload contains `__PLACEHOLDER_n__` or secrets
   - Block if found

**Key function:**
- `createBeforeToolCallHandler(config)` → hook function

### `src/tools/dataguard_read.ts` (Safe File Reading)
**Steps:**
1. Policy check (deny/sanitize verdict)
2. File stat + size check
3. Cache check (mtime + size)
   - Cache hit: return with `cached: true`
   - Cache miss: continue to extraction
4. Extract text (PDF/DOCX/plain)
5. Sanitize (regex + LLM)
6. Cache store
7. Audit log
8. Return sanitized content only

**Key function:**
- `dataguardRead({ path, mode })` → `{ sanitized_text, format, redaction_count, method, cached }`

### `src/tools/dataguard_search.ts` (Sanitized Search)
**Steps:**
1. Check root path
2. Spawn `rg --json` (ripgrep) or fallback to `grep -rn`
3. Parse results
4. Sanitize each snippet individually
5. Return sanitized snippets only

**Key function:**
- `dataguardSearch({ query, root, maxResults })` → `{ snippets, total_matches }`

### `src/tools/dataguard_patch_file.ts` (Permanent Redaction)
**Steps:**
1. Policy check
2. Read file
3. Create backup: `filename.dataguard-backup-<timestamp>`
4. Replace lines with `[REDACTED by DataGuard: <reason>]`
5. Write back to disk
6. Audit log

**Key function:**
- `dataguardPatchFile({ path, ranges, reason })` → `{ lines_redacted, backup_path }`

### `src/tools/dataguard_sanitize_path.ts` (Force Re-sanitize)
**Purpose:** Re-sanitize a file, bypassing cache

**Key function:**
- `dataguardSanitizePath({ path })` → `{ sanitized_path, redaction_count, method, summary }`

### `src/tools/dataguard_policy_explain.ts` (Policy Info)
**Returns:**
- Current policy (allowedRoots, denyPathGlobs, sanitizeAlwaysGlobs, maxFileBytes, etc.)
- Session state (vault entries, placeholder list)
- Usage instructions

**Key function:**
- `dataguardPolicyExplain()` → `{ policy, session, instructions }`

### `src/plugin/index.ts` (Entry Point)
**Responsibilities:**
1. Load config from `~/.openclaw/openclaw.json`
2. Initialize audit logging
3. Initialize cache subsystem
4. Register `before_tool_call` hook
5. Register 5 dataguard_* tools

**Must be synchronous (OpenClaw requirement)**

---

## 🔐 Security Guarantees

### ✅ No External Network Calls
- All Ollama calls to `127.0.0.1:11434` only
- No cloud APIs, no external services
- Will error if Ollama not local

### ✅ Raw Data Never Reaches Main Model
- Native file tools (`Read`, `Glob`, `Grep`) **blocked**
- Agent forced to use `dataguard_*` tools
- Content sanitized before returning

### ✅ Secrets in In-Memory Vault Only
- Placeholder → original mappings in RAM
- Never serialized to disk
- Never in logs or transcripts
- `resolve()` only callable from file-writing code (dataguard_patch_file)

### ✅ Egress Protection
- HTTP/curl/fetch calls blocked if:
  - Payload contains `__PLACEHOLDER_n__`
  - Payload contains secret prefixes (sk-, pk-, ghp-, etc.)

### ✅ Audit Trail
- All decisions logged to JSONL
- Non-fatal: errors don't break tools
- Redaction counts, methods, reasons recorded

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Build
```bash
npm run build
```

Output: `dist/plugin/index.js` (ready to load)

### 3. Register with OpenClaw
```json
{
  "plugins": {
    "entries": {
      "dataguard": {
        "enabled": true,
        "config": {
          "allowedRoots": ["/home/user/my-project"]
        }
      }
    }
  }
}
```

### 4. Start Ollama
```bash
ollama serve &
ollama pull gemma2:latest
```

### 5. Restart OpenClaw
Next time OpenClaw starts, dataguard will be loaded and active.

---

## 📊 Data Flow

```
User/Agent
    │
    ├─ Tries: Read("file.txt")
    │   ↓
    │   [before_tool_call hook]
    │   ├─ Is "read" in BLOCKED_READ_TOOLS? YES
    │   └─ BLOCK with message: "Use dataguard_read instead"
    │
    └─ Corrects: dataguard_read({path: "file.txt"})
        ↓
        [policy.checkPath()]
        ├─ Deny glob? ──► Block
        ├─ Outside allowedRoots? ──► Block
        └─ OK ──► Continue
        ↓
        [cache.get(key)]
        ├─ HIT ──► Return cached
        └─ MISS ──► Continue
        ↓
        [extract.extractText()]
        ├─ Detect format (PDF/DOCX/text)
        └─ Extract text
        ↓
        [sanitize()]
        ├─ Pass 1: detector + vault
        │   └─ Regex + entropy PII detection
        │   └─ Replace with __CATEGORY_n__
        │   └─ Store in vault
        ├─ Pass 2: Ollama Gemma (if available)
        │   └─ Send regex-redacted text
        │   └─ Get further refinements
        │   └─ On error: fallback to regex-only
        └─ Return sanitized_text, redactions, method
        ↓
        [cache.set()]
        └─ Store result for future hits
        ↓
        [audit.log()]
        └─ Record decision
        ↓
        Return to agent:
        {
          sanitized_text: "...__EMAIL_1__...",
          format: "text",
          redaction_count: 1,
          method: "llm+regex",
          cached: false
        }
        ↓
    Agent uses sanitized content
    Secrets protected by placeholders
    Cannot accidentally leak originals
```

---

## 🧪 Testing

### Run Tests
```bash
npm test              # Run all tests
npm run test:watch   # Watch mode
```

### Test Coverage
- `detector.test.ts` — PII detection accuracy
  - Email, SSN, credit card, phone, secrets, entropy
  - Overlap prevention, offset safety
  - Multiple detections with incrementing placeholders

---

## 📝 Configuration Reference

### Default Config
```typescript
{
  denyPathGlobs: [
    "**/.env", "**/.env.*",
    "**/id_rsa*", "**/id_ed25519*", "**/*.pem",
    "**/keychain/**", "**/Keychain/**",
    "**/Library/Application Support/Google/Chrome/**",
    "**/Library/Application Support/Firefox/**",
    "**/.ssh/**"
  ],
  allowedRoots: [process.cwd()],
  sanitizeAlwaysGlobs: [
    "**/*.pdf", "**/*.docx", "**/*.doc",
    "**/docs/**", "**/downloads/**", "**/Downloads/**"
  ],
  maxFileBytes: 5 * 1024 * 1024,
  cacheDir: "~/.openclaw/dataguard/cache",
  auditLogPath: "~/.openclaw/dataguard/audit.jsonl",
  ollamaBaseUrl: "http://127.0.0.1:11434",
  ollamaModel: "gemma2:latest",
  ollamaTimeoutMs: 30_000
}
```

---

## 📦 Dependencies

- **minimatch** ^9.0.5 — Glob pattern matching
- **mammoth** ^1.7.1 — DOCX text extraction
- **pdf-parse** ^1.1.1 — PDF text extraction (fallback)
- **@types/node** ^20.0.0 — Node.js type definitions
- **typescript** ^5.4.0 — TypeScript compiler
- **vitest** ^1.6.0 — Testing framework

No dependencies on:
- `axios`, `node-fetch`, `got` — uses Node built-in `http` module for Ollama
- External cloud services — 100% local

---

## 📂 Key Files to Review

1. **`src/plugin/index.ts`** — Plugin entry point, config loading, hook/tool registration
2. **`src/sanitize/sanitize.ts`** — Core orchestration (regex + LLM)
3. **`src/sanitize/detector.ts`** — PII detection engine (the magic)
4. **`src/hooks/before_tool_call.ts`** — Interception logic
5. **`src/tools/dataguard_read.ts`** — Primary safe read tool (reference for all tools)
6. **`src/tools/dataguard_patch_file.ts`** — File editing / hiding (vault usage)

---

## ✅ Verification Checklist

- [x] TypeScript compiles without errors
- [x] All modules implemented per specification
- [x] Plugin manifest valid (openclaw.plugin.json)
- [x] Hook registration implemented (before_tool_call)
- [x] All 5 tools registered (read, search, patch, sanitize, policy)
- [x] PII detection covers 9 categories + entropy
- [x] Cache keyed by mtime + size (invalidates on write)
- [x] Vault stores placeholders in RAM (never persisted)
- [x] Audit logging to JSONL
- [x] Egress blocking for placeholders/secrets
- [x] Ollama integration (localhost only)
- [x] Fallback to regex-only on LLM failure
- [x] File extraction (PDF, DOCX, text)
- [x] Policy enforcement (deny globs, allowedRoots, etc.)
- [x] Unit tests for detector
- [x] README with complete docs + diagrams
- [x] QUICKSTART.md for fast setup

---

## 🎓 What This Plugin Demonstrates

1. **OpenClaw Plugin API** — How to register hooks and tools
2. **before_tool_call Hook** — Intercepting tool execution
3. **Custom Tool Registration** — Five distinct dataguard_* tools
4. **Synchronous Plugin Loading** — OpenClaw requirement
5. **Local LLM Integration** — Ollama via Node http module
6. **PII Detection** — Regex + entropy scoring
7. **File Format Support** — PDF, DOCX, plain text
8. **In-Memory Vaults** — Secure placeholder storage
9. **File-Based Caching** — Mtime-keyed caching
10. **JSONL Audit Logging** — Append-only decision log

---

## Next Steps

1. **Deploy:** Copy `dist/` to `~/.openclaw/extensions/dataguard/`
2. **Configure:** Add to `~/.openclaw/openclaw.json`
3. **Test:** Run dataguard_read on a real file
4. **Monitor:** Check `~/.openclaw/dataguard/audit.jsonl` for decisions
5. **Extend:** Add more tools (e.g., dataguard_mask for inline redaction) as needed

---

**Built:** February 20, 2024
**Version:** 1.0.0
**Status:** Production-ready
