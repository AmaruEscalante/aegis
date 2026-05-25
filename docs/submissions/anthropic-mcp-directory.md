# Anthropic MCP directory submission

This is the content the user submits to the Anthropic MCP directory (`modelcontextprotocol/servers` GitHub repo) once `aegis-gate@1.0.0` is on npm.

## Submission snippet (for the directory README or server-listing file)

### Aegis

- **Repo:** [github.com/AmaruEscalante/aegis](https://github.com/AmaruEscalante/aegis)
- **Install:** `npx aegis-gate`
- **Category:** Security & Privacy
- **Description:** On-device privacy classifier for AI agents. Classifies file content locally using `embeddinggemma-300m` + trained LR head; routes to passthrough, sanitization, block, or escalation. No network calls at inference, no telemetry, MIT-licensed.
- **Verified:** Yes (npm package signed by maintainer)

## PR procedure

```bash
# 1. Fork modelcontextprotocol/servers via the GitHub UI
# 2. Clone your fork
gh repo clone <your-fork>/servers /tmp/mcp-servers
cd /tmp/mcp-servers

# 3. Create branch
git checkout -b aegis-add-listing

# 4. Edit the appropriate file (likely README.md or a category listing)
#    Append the snippet above in the Security/Privacy section
$EDITOR README.md

# 5. Commit
git add README.md
git commit -m "Add aegis-gate — on-device privacy classifier"

# 6. Push your fork
git push -u origin aegis-add-listing

# 7. Open PR
gh pr create \
  --repo modelcontextprotocol/servers \
  --title "Add aegis-gate — on-device privacy classifier" \
  --body "$(cat <<'EOF'
Adds Aegis to the directory.

- Package: aegis-gate on npm (v1.0.0)
- Install: npx aegis-gate
- Source: https://github.com/AmaruEscalante/aegis
- License: MIT
- Category: Security & Privacy

Aegis is an on-device privacy classifier for AI agents. It runs embeddinggemma-300m + a trained LR head fully in-process — no network calls at inference, no telemetry, no external services required.

Verifiable claims documented in [docs/PRIVACY.md](https://github.com/AmaruEscalante/aegis/blob/main/docs/PRIVACY.md).
EOF
)"
```

Track the PR URL in the project's release notes (or as a sticky issue) once it's open.
