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
# The embedding model (~1.2 GB) — downloaded from HF Hub on first run, cached
ls ~/.cache/huggingface/hub/models--google--embeddinggemma-300m/

# The classifier head (~25 KB) — bundled in the npm package
ls ~/.aegis-gate/middleware/aegis/head/lr.joblib
```

If you delete these files, Aegis will re-download the embedder (since it's HF-cached) but the classifier head is part of the npm install — it doesn't re-download from a separate endpoint.

### 3. No telemetry in the source

```bash
# Search the published source for common telemetry SDKs
grep -rE 'posthog|amplitude|honeycomb|datadog|sentry|google-analytics' ~/.aegis-gate/middleware/dist/ ~/.aegis-gate/middleware/aegis/
```

Returns nothing. The bridge has no analytics imports.

### 4. Audit the source

Aegis is MIT-licensed and the source is at [github.com/AmaruEscalante/aegis](https://github.com/AmaruEscalante/aegis). The TypeScript MCP server is in `middleware/`; the Python bridge + classifier are in `aegis/`. The published npm package is built from these sources without obfuscation.

## What we don't promise

- **Adversarial containment.** Aegis is a cooperative guardrail. It routes `Read`/`Glob`/`Grep` and common single-file `Bash` reads through the classifier, but a determined agent can read files in ways no command-level filter catches (`python -c`, encoding, chunking). For a hard wall, pair Aegis with OS-level sandboxing (`sandbox.filesystem.denyRead`).
- **Image classification.** Image files (`.jpg`, `.png`, etc.) are escalated to you for manual review — they're not classified by the on-device model in v1. OCR support is planned for a future release.
- **Cross-platform identical behavior.** v1 ships macOS-tested. Linux + Windows work in our testing but aren't on the CI matrix yet.
- **Accuracy beyond the documented eval.** The shipped classifier scored 94.90% on a 98-sample held-out eval (see [scorecard.md](eval-results/scorecard.md)). Real-world distribution may differ; we know of one documented fail-open case.

## If you find a privacy issue

Open an issue at [github.com/AmaruEscalante/aegis/issues](https://github.com/AmaruEscalante/aegis/issues) with the label `privacy`. We treat these as high-priority.
