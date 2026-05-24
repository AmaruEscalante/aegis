---
name: aegis
description: Manage the Aegis MCP privacy classifier — status, policy, enable/disable enforcement, uninstall.
---

# Aegis management commands

Slash commands for managing the Aegis MCP plugin from inside Claude Code.

Available commands:
- `/aegis-status` — show current enforcement mode and recent verdicts
- `/aegis-policy` — show classification policy (allow/deny globs, thresholds)
- `/aegis-enable-hook` — enable Read/Glob/Grep enforcement
- `/aegis-disable-hook` — disable enforcement (tools still available, just not forced)
- `/aegis-uninstall` — remove the hook + MCP server config

See [Aegis README](https://github.com/AmaruEscalante/aegis) for full documentation.
