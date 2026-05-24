# Claude Code plugin marketplace submission

Content for the Claude Code marketplace submission form (filed via the Claude Code dashboard).

## Submission fields

```
Plugin name:      aegis-mcp
Description:      On-device privacy classifier for AI agents. Routes Read/Glob/Grep through aegis_read to classify, sanitize, block, or escalate file content locally — no network calls at inference, no telemetry.
Install command:  npx aegis-mcp
Repository:       https://github.com/AmaruEscalante/aegis
Demo:             https://raw.githubusercontent.com/AmaruEscalante/aegis/main/assets/demo.gif
License:          MIT
Category:         Security / Privacy
Maintainer:       Christian Morales Panitz
Contact:          (via GitHub issues at github.com/AmaruEscalante/aegis/issues)
```

## Tagline candidates (one will land in the marketplace listing)

1. "On-device privacy gate for AI agents — install with one command."
2. "Stop AI agents from leaking secrets, PII, and confidential docs."
3. "Local-only privacy layer for Claude Code. 94.90% accuracy, ~78 ms latency."

(The marketplace form likely has a character limit; pick #1 or #2 depending on which the form accepts.)

## Submission procedure

1. Sign in to the Claude Code dashboard (your account)
2. Navigate to the Plugin Marketplace submissions page
3. Fill in the form fields with the values above
4. Attach a screen recording or link to the demo GIF (raw GitHub URL)
5. Submit

Track the submission ID in the project's release notes once it's filed. Marketplace review typically takes 1-2 weeks.

## Post-submission checklist

After both Anthropic MCP directory PR (T14) and Claude Code marketplace submission (T15) are filed:

- [ ] PR URL recorded in release notes
- [ ] Marketplace submission ID recorded
- [ ] Watch for review feedback; respond promptly
- [ ] Once approved, announce on relevant channels (HN, Twitter, etc. — at your discretion)
