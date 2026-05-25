# aegis-gate middleware

TypeScript MCP server for Aegis. This is the package published to npm as `aegis-gate` and invoked by `npx aegis-gate`.

Companion to `aegis/` (Python bridge) at the repo root.

## What it does

Exposes four MCP tools to Claude Code (and any MCP client):

- `aegis_read` — read a file, classify it, route based on verdict
- `aegis_classify` — classify without returning content
- `aegis_policy_explain` — show the current policy
- `aegis_sanitize_path` — force re-sanitization

On startup:
1. Detects Python 3.12+ on PATH
2. Ensures `~/.aegis-gate/venv/` with pinned deps from `aegis/requirements.txt`
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
  cli.ts              # `npx aegis-gate` entry point
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
