## Aegis Privacy Layer — File Access Rules

This project has an Aegis MCP server configured. You MUST follow these rules when reading files.

### MANDATORY: Use Aegis tools for ALL file reads

**NEVER use the built-in Read, Glob, or Grep tools to read file contents.** Always use the Aegis MCP tools instead:

- **`aegis_read`** — Use this instead of `Read`. It classifies the file on-device, then either passes through (safe), sanitizes PII, blocks secrets, or asks for human permission.
- **`aegis_classify`** — Use this to check a file's sensitivity before reading it. Returns verdict (safe/flag_pii/block/escalate) without returning content.
- **`aegis_policy_explain`** — Use this to see current security policy and what's been redacted this session.
- **`aegis_sanitize_path`** — Use this to force re-sanitization of a file.

### How to read a file

Instead of:
```
Read({ path: "data/users.csv" })
```

Do:
```
aegis_read({ path: "data/users.csv" })
```

### What happens

- **Safe files** come back unchanged (zero overhead)
- **PII files** come back with placeholders like `__EMAIL_1__`, `__SSN_1__` replacing sensitive data
- **Secret files** (.env, API keys, credentials) are blocked — you'll get an error, never the content
- **Ambiguous files** (contracts, financials) return an escalation asking you to get user permission first

### Prerequisites

The Aegis bridge must be running for classification to work:
```bash
uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter
```

If the bridge is down, Aegis degrades gracefully to sanitize-everything mode (all files get PII-scrubbed).

## NEVER EVER DO

These rules are ABSOLUTE:

### NEVER Publish Sensitive Data
- NEVER publish passwords, API keys, tokens to git/npm/docker
- Before ANY commit: verify no secrets included

### NEVER Commit .env Files
- NEVER commit `.env` to git
- ALWAYS verify `.env` is in `.gitignore`

### NEVER Hardcode Credentials
- ALWAYS use environment variables
