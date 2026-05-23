---
name: aegis-policy
description: Show Aegis classification policy (allow/deny globs, verdict thresholds).
---

When the user invokes `/aegis-policy`:

1. Call the `aegis_policy_explain` MCP tool with no arguments
2. Display the returned policy info to the user
