---
name: aegis-uninstall
description: Remove Aegis hook, MCP server config, and skill registration.
---

When the user invokes `/aegis-uninstall`:

1. Confirm with the user: "This will remove the Aegis hook, MCP server config, and slash command skill. Cached Python venv and embedding model at ~/.aegis-gate/ will be preserved unless the user explicitly deletes them. Continue? [y/N]"
2. On `y`, run `node ~/.aegis-gate/skills/aegis/scripts/uninstall.js`
3. Report the result
