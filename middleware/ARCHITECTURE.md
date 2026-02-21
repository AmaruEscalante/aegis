# DataGuard Architecture & Design

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ OpenClaw Agent                                                       │
│ (Claude or other LLM)                                              │
└─────────────────────┬───────────────────────────────────────────────┘
                      │ Calls tools
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ OpenClaw Runtime / Plugin Gateway                                   │
│                                                                     │
│  ├─ before_tool_call HOOK (dataguard)                              │
│  │  ├─ Is it Read/Glob/Grep? ──► BLOCK                            │
│  │  ├─ Is it HTTP with secrets? ──► BLOCK                         │
│  │  └─ Otherwise: ALLOW                                           │
│  │                                                                 │
│  └─ Tool registry                                                  │
│     ├─ dataguard_read                                             │
│     ├─ dataguard_search                                           │
│     ├─ dataguard_patch_file                                       │
│     ├─ dataguard_sanitize_path                                    │
│     └─ dataguard_policy_explain                                   │
└─────────────────────┬───────────────────────────────────────────────┘
                      │ Tool execution
                      ▼
┌──────────────────────────────────────────────────────────┐
│ DataGuard Plugin (sanitize module)                       │
│                                                         │
│ ┌──────────────────────────────────────────────────┐  │
│ │ Tool Handlers (dataguard_read, etc.)             │  │
│ │ ├─ Check policy (deny/allow)                     │  │
│ │ ├─ Check file size                               │  │
│ │ └─ Orchestrate sanitization pipeline             │  │
│ └─────────────────┬──────────────────────────────┘  │
│                   │                                   │
│ ┌─────────────────▼──────────────────────────────┐  │
│ │ Cache Layer (mtime + size keyed)               │  │
│ │ ├─ Hit: return cached sanitized result         │  │
│ │ └─ Miss: continue to extraction                │  │
│ └─────────────────┬──────────────────────────────┘  │
│                   │                                   │
│ ┌─────────────────▼──────────────────────────────┐  │
│ │ Extract Module (PDF/DOCX/Text)                 │  │
│ │ ├─ PDF: pdftotext or pdf-parse                 │  │
│ │ ├─ DOCX: mammoth                               │  │
│ │ └─ Text: fs.readFileSync                       │  │
│ └─────────────────┬──────────────────────────────┘  │
│                   │                                   │
│ ┌─────────────────▼──────────────────────────────┐  │
│ │ Sanitization (Pass 1: Regex + Entropy)         │  │
│ │ ├─ detect(): find PII/secrets                  │  │
│ │ │  ├─ 8 regex patterns                         │  │
│ │ │  ├─ Secret prefix detection                  │  │
│ │ │  └─ Shannon entropy scoring                  │  │
│ │ ├─ applyRedactions(): replace with __X_n__     │  │
│ │ └─ vault.addMappings(): store originals        │  │
│ └─────────────────┬──────────────────────────────┘  │
│                   │                                   │
│ ┌─────────────────▼──────────────────────────────┐  │
│ │ Sanitization (Pass 2: Ollama Gemma - Optional) │  │
│ │ ├─ Build prompt (regex-redacted text)          │  │
│ │ ├─ HTTP POST to 127.0.0.1:11434/api/chat      │  │
│ │ ├─ Parse JSON response                         │  │
│ │ ├─ Merge LLM findings with regex results       │  │
│ │ └─ On failure: fall back to regex-only         │  │
│ └─────────────────┬──────────────────────────────┘  │
│                   │                                   │
│ ┌─────────────────▼──────────────────────────────┐  │
│ │ Cache Write + Audit Log                        │  │
│ │ ├─ Store sanitized artifact in cache           │  │
│ │ └─ Append decision to audit.jsonl              │  │
│ └─────────────────┬──────────────────────────────┘  │
│                   │                                   │
│ ┌─────────────────▼──────────────────────────────┐  │
│ │ Return Sanitized Content                       │  │
│ │ ├─ sanitized_text (with __X_n__ placeholders)  │  │
│ │ ├─ redaction_count, method used                │  │
│ │ └─ format, cache status                        │  │
│ └──────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│ OpenClaw Agent receives ONLY SANITIZED CONTENT                      │
│                                                                     │
│ Content has __EMAIL_1__, __SECRET_2__, etc. placeholders           │
│ Original values stored ONLY in plugin vault (RAM, not accessible) │
│ Agent cannot leak secrets even if tries to exfiltrate             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Module Dependency Graph

```
plugin/index.ts (entry point)
    │
    ├─► hooks/before_tool_call.ts
    │   └─► sanitize/policy.ts
    │       └─► minimatch (for glob matching)
    │
    ├─► tools/dataguard_read.ts
    │   ├─► sanitize/policy.ts
    │   ├─► sanitize/extract.ts
    │   │   ├─► fs (built-in)
    │   │   ├─► child_process (pdftotext shell-out)
    │   │   ├─► mammoth (DOCX)
    │   │   └─► pdf-parse (PDF fallback)
    │   ├─► sanitize/sanitize.ts
    │   │   ├─► sanitize/detector.ts
    │   │   ├─► sanitize/prompts.ts
    │   │   └─► sanitize/vault.ts
    │   ├─► sanitize/cache.ts
    │   │   └─► crypto (for SHA-256)
    │   └─► sanitize/audit.ts
    │       └─► fs (for JSONL append)
    │
    ├─► tools/dataguard_search.ts
    │   ├─► sanitize/policy.ts
    │   ├─► sanitize/sanitize.ts
    │   ├─► child_process (for rg/grep)
    │   └─► sanitize/audit.ts
    │
    ├─► tools/dataguard_patch_file.ts
    │   ├─► sanitize/policy.ts
    │   └─► sanitize/audit.ts
    │
    ├─► tools/dataguard_sanitize_path.ts
    │   ├─► sanitize/policy.ts
    │   ├─► sanitize/extract.ts
    │   ├─► sanitize/sanitize.ts
    │   ├─► sanitize/cache.ts
    │   └─► sanitize/audit.ts
    │
    └─► tools/dataguard_policy_explain.ts
        └─► sanitize/vault.ts

Core Singletons (module-level):
    ├─ sanitize/vault.ts
    │   └─ store: Map<placeholder, original>
    ├─ sanitize/cache.ts
    │   └─ cacheDir: path
    └─ sanitize/audit.ts
        └─ auditFilePath: path
```

---

## Data Structures

### Detection Object
```typescript
interface Detection {
  category: PiiCategory;        // EMAIL, PHONE, SSN, etc.
  value: string;                // Original matched text
  start: number;                // Char offset in source
  end: number;
  placeholder: string;          // __CATEGORY_n__
}
```

### Sanitization Result
```typescript
interface SanitizeResult {
  sanitized_text: string;       // Text with __X_n__ replacements
  redactions: Detection[];      // What was replaced
  llm_summary?: string;         // From Ollama (optional)
  method: "llm+regex" | "regex-only";
}
```

### Cache Key & Entry
```typescript
interface CacheKey {
  absolutePath: string;
  mtime: number;                // From fs.statSync().mtimeMs
  size: number;                 // File size in bytes
}

interface CacheEntry {
  sanitizedText: string;
  redactions: Detection[];
  method: string;
  cachedAt: number;             // Date.now()
}
```

### Vault Entry
```typescript
interface VaultEntry {
  placeholder: string;          // __EMAIL_1__
  original: string;             // alice@example.com
  category: PiiCategory;
  addedAt: number;              // Date.now()
}
```

---

## PII Detection Flow

```
Input Text
    │
    ▼
┌─────────────────────────────────────────┐
│ PASS 1: Regex Matching                  │
│                                         │
│ Patterns (in order):                    │
│ ├─ SSN: \d{3}-\d{2}-\d{4}              │
│ ├─ CREDIT_CARD: \d{16,19}              │
│ ├─ IBAN: [A-Z]{2}\d{2}[A-Z0-9]{4,30}  │
│ ├─ PHONE: \(\d{3}\) \d{3}-\d{4}       │
│ ├─ EMAIL: user@domain.com              │
│ ├─ IP_ADDRESS: \d{1,3}\.\d{1,3}...    │
│ ├─ URL: https?://...                   │
│ └─ SECRET: sk-..., pk_..., ghp_, etc.  │
│                                         │
│ Store in: covered set (prevent overlap) │
│ Generate: __CATEGORY_n__ placeholders   │
│                                         │
│ Output: [Detection, Detection, ...]     │
└─────────────┬───────────────────────────┘
              │
    ┌─────────▼─────────┐
    │  "covered" set    │
    │  prevents double- │
    │  tagging          │
    └───────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ PASS 2: Shannon Entropy Scoring         │
│                                         │
│ For tokens (≥20 chars, not in covered): │
│ ├─ Calculate Shannon entropy            │
│ ├─ If entropy ≥ 4.0 bits: flag as      │
│ │  HIGH_ENTROPY secret                  │
│ └─ Generate: __HIGH_ENTROPY_n__        │
│                                         │
│ Output: Additional Detections           │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ MERGE & SORT                            │
│                                         │
│ ├─ Combine regex + entropy detections   │
│ ├─ Sort by start offset (ascending)     │
│ └─ Return: Detection[] (offset-safe)    │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ APPLY REDACTIONS (left-to-right)        │
│                                         │
│ cursor = 0                              │
│ for each Detection (sorted by offset):  │
│   ├─ Append text[cursor..start)        │
│   ├─ Append detection.placeholder      │
│   └─ cursor = detection.end            │
│ Append text[cursor..end)               │
│                                         │
│ Output: Sanitized text                  │
└─────────────┬───────────────────────────┘
              │
              ▼
Sanitized Text with __X_n__ placeholders
```

---

## Policy Decision Tree

```
checkPath(rawPath, config)
    │
    ▼
┌──────────────────────────────────┐
│ Check Deny Globs                 │
│ (using minimatch)                │
│                                  │
│ ├─ **/.env                       │
│ ├─ **/.env.*                     │
│ ├─ **/id_rsa*                    │
│ ├─ **/keychain/**                │
│ └─ ... (user configured)         │
│                                  │
│ Match? ──► DENY                  │
└──────────────────────────────────┘
              │ no match
              ▼
┌──────────────────────────────────┐
│ Check Allowed Roots              │
│                                  │
│ Is path under any of:            │
│ config.allowedRoots?             │
│                                  │
│ NO ──► DENY                      │
└──────────────────────────────────┘
              │ YES
              ▼
┌──────────────────────────────────┐
│ Check Sanitize-Always Globs      │
│                                  │
│ ├─ **/*.pdf                      │
│ ├─ **/*.docx                     │
│ ├─ **/docs/**                    │
│ └─ ... (user configured)         │
│                                  │
│ Match? ──► SANITIZE              │
└──────────────────────────────────┘
              │ no match
              ▼
    Default: SANITIZE
```

---

## Cache Invalidation

```
┌─────────────────────────────────────────┐
│ Cache Key = SHA-256(path|mtime|size)    │
└─────────────────────────────────────────┘

When file is read:
    ├─ Call fs.statSync()
    ├─ Extract: mtime, size
    ├─ Hash key
    └─ Look up in cache

CACHE HIT if:
    ├─ mtime unchanged (file not modified)
    └─ size unchanged

CACHE MISS if:
    ├─ File modified (mtime changed) ──► RE-SANITIZE
    ├─ File size changed ──► RE-SANITIZE
    └─ First access (key not in cache) ──► SANITIZE

Special case:
    ├─ File metadata changed (chmod) but mtime/size same
    └─ Still returns cached (acceptable; content unchanged)
```

---

## Vault Lifecycle

```
┌─────────────────────────────────────────┐
│ Plugin Loaded (OpenClaw startup)        │
│                                         │
│ vault: Map<placeholder, VaultEntry> {} │
│ (empty, in-memory only)                 │
└─────────────────────────────────────────┘
              │
              ▼ (on first dataguard_read)
┌─────────────────────────────────────────┐
│ PII Detected (detector + vault)         │
│                                         │
│ vault.addMappings([                     │
│   {placeholder: "__EMAIL_1__",          │
│    original: "alice@example.com",       │
│    category: "EMAIL"}                   │
│ ])                                      │
│                                         │
│ vault.store:                            │
│   "__EMAIL_1__" → VaultEntry{...}      │
└─────────────────────────────────────────┘
              │
              ▼ (if agent calls dataguard_patch_file)
┌─────────────────────────────────────────┐
│ File Editing (uses vault.resolve)       │
│                                         │
│ original = vault.resolve("__EMAIL_1__")│
│ ──► "alice@example.com"                │
│ (used only to write to disk)            │
│                                         │
│ NEVER returned to agent/LLM             │
└─────────────────────────────────────────┘
              │
              ▼ (on session end / process exit)
┌─────────────────────────────────────────┐
│ Plugin Unloaded                         │
│                                         │
│ vault.store cleared (garbage collected) │
│ All placeholder mappings destroyed      │
│ Secrets gone from memory                │
└─────────────────────────────────────────┘
```

---

## LLM Integration (Ollama)

```
┌─────────────────────────────────────┐
│ Sanitize (text, config)             │
└─────────────────┬───────────────────┘
                  │
                  ▼
     ┌────────────────────────────┐
     │ Pass 1: Regex Detection    │
     │ Output: regexRedacted text │
     └────────────┬───────────────┘
                  │
                  ▼
     ┌──────────────────────────────────┐
     │ Try LLM Pass (Ollama)            │
     │                                  │
     │ buildSanitizePrompt(            │
     │   text: original,               │
     │   regexRedacted: pre-redacted   │
     │ )                                │
     │                                  │
     │ POST to 127.0.0.1:11434/api/chat│
     │ {model: "gemma2:latest", ...}   │
     │                                  │
     │ Timeout: config.ollamaTimeoutMs │
     └────────────┬────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
    SUCCESS            FAILURE/TIMEOUT
         │                 │
         ▼                 ▼
    ┌─────────────┐  ┌──────────────┐
    │ Parse JSON  │  │ Fall back to │
    │ Merge LLM   │  │ regex-only   │
    │ findings    │  │ result       │
    │ with regex  │  └──────────────┘
    └─────────────┘         │
         │                  │
         └──────┬───────────┘
                ▼
    ┌──────────────────────┐
    │ SanitizeResult       │
    │ {                    │
    │   sanitized_text,    │
    │   redactions,        │
    │   method,            │
    │   llm_summary?       │
    │ }                    │
    └──────────────────────┘
```

---

## Audit Log Schema

```jsonl
{
  "timestamp": "2024-02-20T10:15:23.456Z",
  "event": "dataguard_read",
  "toolName": "dataguard_read",
  "path": "/home/user/config.txt",
  "action": "sanitize",
  "redactionCount": 3,
  "method": "llm+regex",
  "reason": null
}

{
  "timestamp": "2024-02-20T10:15:24.123Z",
  "event": "before_tool_call",
  "toolName": "read",
  "action": "block",
  "reason": "Use dataguard_read / dataguard_search instead of native file tools"
}

{
  "timestamp": "2024-02-20T10:15:25.789Z",
  "event": "dataguard_patch_file",
  "path": "/home/user/log.txt",
  "action": "patch",
  "reason": "contains customer SSN",
  "redactionCount": 5
}
```

---

## Thread Safety & Concurrency

**Current implementation: NOT thread-safe**

Assumptions:
- Single-threaded Node.js environment (V8 per-isolate)
- OpenClaw runs one agent per process
- Vault/cache singletons OK within process lifetime
- JSONL audit log: concurrent appends may interleave (acceptable for audit log)

If multi-threaded support needed:
- Use `node:worker_threads` with shared vault
- Or: move vault to external store (Redis, SQLite)
- Or: per-worker vault with UUID session tracking

---

## Error Handling Philosophy

1. **Policy violations** (deny path, file not found, etc.) → Throw error
2. **Tool logic errors** → Throw with descriptive message
3. **Cache failures** → Non-fatal; continue without cache
4. **Audit log failures** → Non-fatal; never break tool
5. **LLM failures** (timeout, connection error) → Fallback to regex-only, never throw
6. **File extraction failures** → Throw with format-specific message

Principle: **Errors in core logic are fatal; errors in nice-to-have features are not.**

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Cache hit | ~1 ms | File stat + map lookup |
| Regex only | 5–50 ms | Depends on file size, # patterns |
| Regex + LLM | 500–2000 ms | Ollama model cold-start ~15–30s, subsequent calls faster |
| PDF extract | 100–500 ms | pdftotext or pdf-parse |
| DOCX extract | 50–200 ms | mammoth package |
| Cache write | 10–50 ms | Two-level dir sharding |
| Audit log | <1 ms | Append to JSONL (non-blocking) |

---

## Extensibility Points

To add new features:

1. **New detection category:**
   - Add regex to `detector.ts`
   - Update `PiiCategory` type

2. **New file format (e.g., RTF, Pages):**
   - Add case to `extract.ts`
   - Implement extraction function

3. **New egress block (e.g., Slack API):**
   - Add to `EGRESS_TOOLS` set in `before_tool_call.ts`

4. **New tool (e.g., dataguard_mask for inline redaction):**
   - Create `src/tools/dataguard_mask.ts`
   - Register in `plugin/index.ts`
   - Add to tool registry

5. **Different LLM (e.g., local llama.cpp):**
   - Modify `sanitize.ts` LLM endpoint switching
   - Add config option for base URL

---

## Security Assumptions

1. OpenClaw process runs with current user permissions (no privilege escalation)
2. Ollama runs on localhost, accessible only from OpenClaw process
3. Filesystem permissions respected (plugin cannot access files current user cannot read)
4. No malicious plugins loaded alongside dataguard
5. Process memory isolated (VM/container)
6. No filesystem monitoring tools interceping file I/O

---

**End of Architecture Documentation**
