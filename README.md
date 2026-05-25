# Aegis — On-Device Privacy Gate for AI Agents

> **On-device, by default.** Aegis classifies files locally before any AI agent reads them — weights are bundled at install, no network calls at inference, no telemetry. Verify it yourself: see [PRIVACY.md](docs/PRIVACY.md) for the receipts.

```
npx aegis-gate
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
- **Weights are local** — `~/.cache/huggingface/hub/models--google--embeddinggemma-300m/` (model) + `~/.aegis-gate/middleware/aegis/head/lr.joblib` (classifier head).
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
npx aegis-gate
```

On first run:
1. Prompts to install the Read/Glob/Grep enforcement hook (default Yes)
2. Sets up the Python bridge venv at `~/.aegis-gate/venv/`
3. Downloads the embedding model on first classification (~1.2 GB, cached)
4. Registers slash commands: `/aegis-status`, `/aegis-policy`, `/aegis-enable-hook`, `/aegis-disable-hook`, `/aegis-uninstall`

### Requirements
- Python 3.12+ on PATH
- Claude Code (or any MCP-compatible client)
- ~1.5 GB disk for the cached model + venv

### Uninstall
```bash
npx aegis-gate uninstall
```

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) — coming with v1.1.

## License

MIT — see [LICENSE](LICENSE).
