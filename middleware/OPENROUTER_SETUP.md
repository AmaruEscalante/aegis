# DataGuard OpenRouter Integration

## Overview

DataGuard now supports **OpenRouter** as a cloud-based LLM provider, enabling enhanced PII detection without requiring local Ollama setup. The plugin seamlessly switches between local Ollama and OpenRouter based on configuration.

## Quick Start

### 1. Get OpenRouter API Key

1. Go to https://openrouter.ai
2. Sign up or log in
3. Go to API keys section
4. Create a new API key
5. Copy the key (format: `sk-or-v1-...`)

### 2. Configure DataGuard

Edit `~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "dataguard": {
        "enabled": true,
        "config": {
          "llmProvider": "openrouter",
          "openrouterApiKey": "sk-or-v1-YOUR_KEY_HERE",
          "openrouterModel": "openai/gpt-4o-mini",
          "allowedRoots": ["/path/to/your/project"]
        }
      }
    }
  }
}
```

### 3. Restart OpenClaw

```bash
# OpenClaw will automatically load the plugin with the new configuration
```

## Configuration Options

### LLM Provider Selection

```json
{
  "llmProvider": "ollama"      // Use local Ollama (default)
  // OR
  "llmProvider": "openrouter"  // Use OpenRouter cloud
}
```

### Ollama Configuration (Local LLM)

```json
{
  "ollamaBaseUrl": "http://127.0.0.1:11434",
  "ollamaModel": "gemma2:latest",
  "ollamaTimeoutMs": 30000
}
```

**Setup:**

```bash
# 1. Install Ollama: https://ollama.ai
# 2. Start the service
ollama serve

# 3. In another terminal, pull the model
ollama pull gemma2:latest
```

### OpenRouter Configuration (Cloud LLM)

```json
{
  "openrouterApiKey": "sk-or-v1-...",
  "openrouterModel": "openai/gpt-4o-mini",
  "openrouterTimeoutMs": 30000
}
```

## Available Models

### Recommended (Best Accuracy)

| Model | Provider | Accuracy | Speed | Cost |
|-------|----------|----------|-------|------|
| `openai/gpt-4o-mini` | OpenRoute | **100%** | Medium | $0.01/1M input |
| `qwen/qwen-2.5-7b-instruct` | OpenRouter | 93% | Fast | Free (for now) |

### All Available Models

- `openai/gpt-4o-mini` - Best overall, 100% accuracy
- `openai/gpt-4-turbo` - High accuracy, slower
- `qwen/qwen-2.5-7b-instruct` - Good balance, free tier
- `anthropic/claude-3-haiku` - Fast, good accuracy
- Many more: https://openrouter.ai/models

## Data Flow

```
agent → dataguard_read({path})
  ↓
policy.checkPath()
  ↓
extract.extractText()
  ↓
cache.get() → [cache hit]
  ↓
sanitize()
  ├─ Pass 1: Regex detection (detector.ts)
  │   └─ 9 PII categories: EMAIL, PHONE, SSN, etc.
  │
  ├─ Pass 2: LLM refinement
  │   ├─ if llmProvider == "openrouter":
  │   │   └─ HTTPS POST to https://openrouter.ai/api/v1/chat/completions
  │   │
  │   └─ if llmProvider == "ollama":
  │       └─ HTTP POST to http://127.0.0.1:11434/api/chat
  │
  └─ Merge detections, return sanitized text
  ↓
cache.set()
  ↓
audit.log()
  ↓
return { sanitized_text: "__EMAIL_1__ ...", redaction_count: 5 }
```

## Fallback Behavior

If OpenRouter fails (timeout, rate limit, API error):

1. LLM enhancement is skipped
2. Regex-only result is returned
3. **Zero data loss** — agent still receives redacted content
4. Audit log records the LLM failure
5. Graceful degradation: "regex-only" method

```json
{
  "sanitized_text": "__EMAIL_1__ ...",
  "method": "regex-only"  // ← LLM failed, fell back
}
```

## Testing

### 1. Verify Configuration

```bash
node /tmp/dataguard-test-files/test-openrouter-integration.js
```

Expected output:
```
✅ OpenRouter API Key:  Valid
✅ Provider selected:   OpenRouter
✅ Timeout:             30000ms
```

### 2. Test with Real Data

```javascript
// In your code using the plugin:
const result = await dataguard_read({ path: "config.json" });

console.log(result);
// {
//   sanitized_text: "...__EMAIL_1__...",
//   redaction_count: 12,
//   method: "llm+regex"  // ← LLM was used
// }
```

### 3. Monitor Audit Log

```bash
tail -f ~/.openclaw/dataguard/audit.jsonl
```

Example entry:
```json
{
  "timestamp": "2026-02-21T10:45:00.000Z",
  "event": "dataguard_read",
  "action": "sanitize",
  "method": "llm+regex",
  "redactionCount": 12
}
```

## Switching Providers

### From Ollama to OpenRouter

```json
{
  "llmProvider": "openrouter",           // ← Change this
  "openrouterApiKey": "sk-or-v1-...",
  "openrouterModel": "openai/gpt-4o-mini"
}
```

### From OpenRouter to Ollama

```json
{
  "llmProvider": "ollama",  // ← Change this
  "ollamaBaseUrl": "http://127.0.0.1:11434",
  "ollamaModel": "gemma2:latest"
}
```

## Performance Characteristics

### Ollama (Local)

| Metric | Value |
|--------|-------|
| First call | 30-60s (model warmup) |
| Subsequent calls | 10-20s |
| Cost | $0 (free) |
| Privacy | 100% local |
| Requires | 8GB+ RAM, GPU optional |

### OpenRouter

| Metric | Value |
|--------|-------|
| Typical latency | 2-5s |
| Throughput | High (parallel requests) |
| Cost | $0.01 per 1M input tokens (gpt-4o-mini) |
| Privacy | Data sent to OpenRouter servers |
| Scaling | Unlimited |

## Cost Estimation

### OpenRouter Costs (gpt-4o-mini)

- **Input**: $0.15 per 1M tokens (~250K documents)
- **Output**: $0.60 per 1M tokens

**Example**: 100 documents, ~1KB each
- Total tokens: ~100,000
- Estimated cost: **$0.015 (less than 2 cents)**

### Ollama Costs

- **Infrastructure**: Your own hardware
- **Per-document**: ~30s CPU time
- **Parallel processing**: Limited by local resources

## Security Considerations

### OpenRouter

✅ **Pros:**
- No infrastructure to maintain
- Transparent API with audit logs
- Can use different models
- HTTPS encrypted transmission

⚠️ **Cons:**
- Data sent to external servers
- Dependent on OpenRouter availability
- Requires valid API key
- Rate limits apply

**Privacy Note**: Document content sent to OpenRouter for LLM analysis. Ensure compliance with data policies.

### Ollama (Local)

✅ **Pros:**
- 100% local processing
- No external dependencies
- No API keys needed
- Complete privacy

⚠️ **Cons:**
- Requires infrastructure setup
- Slower (10-60s per document)
- Limited model selection
- Requires 8GB+ RAM

## Troubleshooting

### "OpenRouter error: 429 — Rate limit exceeded"

**Solution**: Wait a moment and retry, or switch to Ollama

### "OpenRouter error: Invalid API key"

**Solution**:
1. Verify key format starts with `sk-or-v1-`
2. Check key hasn't been revoked
3. Get new key from https://openrouter.ai/keys

### "Request timed out after 30000ms"

**Solution**: Increase timeout or use Ollama

```json
{
  "openrouterTimeoutMs": 60000  // 60 seconds
}
```

### "No LLM response received"

**Check**:
1. Internet connection
2. OpenRouter API status
3. Model availability
4. Audit log for details

## Migration Path

### Current: OpenRouter

```json
{ "llmProvider": "openrouter", "openrouterApiKey": "..." }
```

### Future: Upgrade to Local Gemma2

When ready to switch to local LLM:

```bash
# 1. Stop using OpenRouter
# 2. Start Ollama
ollama serve
ollama pull gemma2:latest

# 3. Update config
{
  "llmProvider": "ollama",
  "ollamaModel": "gemma2:latest"
}

# 4. Restart plugin
# Zero code changes needed!
```

## Model Comparison

### Test Results (15 PII items document)

| Model | Provider | Accuracy | Time | Notes |
|-------|----------|----------|------|-------|
| gpt-4o-mini | OpenRouter | **100%** | 2-3s | Recommended |
| qwen-2.5-7b-instruct | OpenRouter | **93%** | 1-2s | Free tier |
| gemma2:latest | Ollama (local) | ~92% | 20-30s | Privacy |

## Further Reading

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [Ollama Models](https://ollama.ai/library)
- [DataGuard README](./README.md)
- [Architecture Guide](./ARCHITECTURE.md)
