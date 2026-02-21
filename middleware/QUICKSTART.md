# DataGuard — Quick Start Guide

## 30-Second Setup

### 1. Install & Build

```bash
cd /home/andres/base_last_hackathon/dataguard
npm install
npm run build
```

### 2. Register with OpenClaw

Edit `~/.openclaw/openclaw.json`:

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

### 3. Start Ollama

```bash
# Terminal 1:
ollama serve

# Terminal 2:
ollama pull gemma2:latest
```

### 4. Restart OpenClaw

Now when OpenClaw starts, dataguard will be loaded.

---

## Test It

Try to read a file:

```
User: "Show me the config file"

Agent:
  ❌ Tool 'read' is blocked by DataGuard.
     Use dataguard_read({path}) or dataguard_search({query, root}) to access files safely.

Agent (corrects):
  ✅ dataguard_read({path: "config.json"})
```

---

## Key Features

| Feature | How to Use |
|---------|-----------|
| **Read files safely** | `dataguard_read({path})` |
| **Search files** | `dataguard_search({query, root})` |
| **Permanently hide content** | `dataguard_patch_file({path, ranges, reason})` |
| **Force re-sanitization** | `dataguard_sanitize_path({path})` |
| **Check policy** | `dataguard_policy_explain()` |

---

## Core Idea

```
Raw file access BLOCKED
         ↓
Agent forced to use dataguard_read()
         ↓
PII/secrets detected via regex + Ollama Gemma
         ↓
Original stored in vault (never visible externally)
         ↓
Agent receives sanitized content with __PLACEHOLDER_n__
         ↓
Egress tools checked for placeholders/secrets (BLOCKED if found)
         ↓
100% local, 100% safe
```

---

## Configuration Options

```json
{
  "dataguard": {
    "config": {
      "allowedRoots": ["/path/to/project"],
      "denyPathGlobs": ["**/.env", "**/id_rsa*"],
      "sanitizeAlwaysGlobs": ["**/*.pdf", "**/docs/**"],
      "maxFileBytes": 5242880,
      "ollamaBaseUrl": "http://127.0.0.1:11434",
      "ollamaModel": "gemma2:latest",
      "ollamaTimeoutMs": 30000
    }
  }
}
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Ollama request timed out" | Check `ollama serve` is running, increase `ollamaTimeoutMs` |
| "Path not under allowed root" | Add directory to `allowedRoots` |
| "File exceeds maxFileBytes" | Increase `maxFileBytes` in config |
| "Tool blocked by DataGuard" | Use `dataguard_read` instead of `Read` |

---

## Audit Log

View all access decisions:

```bash
cat ~/.openclaw/dataguard/audit.jsonl | jq .
```

---

## For More Details

See [README.md](./README.md) for complete documentation, architecture diagrams, and examples.
