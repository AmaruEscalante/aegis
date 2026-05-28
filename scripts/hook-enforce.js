#!/usr/bin/env node
/**
 * Aegis PreToolUse hook — redirect file reads to the aegis_read MCP tool.
 *
 * Read/Glob/Grep: always redirected.
 * Bash: redirected only when the command is a simple single-file read
 *   (cat/head/grep FILE, etc.), as classified by detect-bash-read. Anything
 *   ambiguous (pipes/substitution/redirection/chaining/indirect interpreters)
 *   fails open — Aegis is a cooperative guardrail, not adversarial containment.
 *
 * Emits the documented PreToolUse decision schema:
 *   { hookSpecificOutput: { hookEventName, permissionDecision: "deny", permissionDecisionReason } }
 *
 * Protocol reference: https://code.claude.com/docs/en/hooks
 */

const path = require('node:path');

const READ_TOOLS = new Set(['Read', 'Glob', 'Grep']);

// detect-bash-read is compiled TS. Its location differs between a dev checkout
// (<repo>/scripts -> <repo>/middleware/dist) and the installed/staged package
// (<root>/middleware/scripts -> <root>/middleware/dist). Try both; if neither
// loads, fall back to "not a read" (fail open) so Bash never breaks.
function loadDetector() {
  const candidates = [
    path.join(__dirname, '..', 'dist', 'detect-bash-read.js'),                 // installed/staged
    path.join(__dirname, '..', 'middleware', 'dist', 'detect-bash-read.js'),   // dev checkout
  ];
  for (const c of candidates) {
    try {
      return require(c).detectBashRead;
    } catch {
      // try next candidate
    }
  }
  return null;
}

function deny(reason) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason: reason,
      },
    }) + '\n',
  );
  process.exit(0);
}

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { raw += chunk; });
process.stdin.on('end', () => {
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch (e) {
    // Can't parse → fail open so we never brick Claude Code.
    console.error(`[aegis-hook] failed to parse hook payload: ${e.message}`);
    process.exit(0);
  }

  const toolName = payload?.tool_name;

  if (READ_TOOLS.has(toolName)) {
    deny(
      `Aegis is active — use aegis_read instead of ${toolName} for file content. ` +
        `Aegis classifies the file on-device and either passes it through, sanitizes PII, ` +
        `blocks credentials, or escalates to the user. See /aegis-status for current policy.`,
    );
  }

  if (toolName === 'Bash') {
    const command = payload?.tool_input?.command;
    if (typeof command !== 'string' || command.length === 0) {
      process.exit(0); // nothing to classify → allow
    }
    const detectBashRead = loadDetector();
    if (!detectBashRead) {
      process.exit(0); // detector unavailable → fail open
    }
    let result;
    try {
      result = detectBashRead(command);
    } catch (e) {
      console.error(`[aegis-hook] detectBashRead threw: ${e.message}`);
      process.exit(0); // fail open
    }
    if (result && result.isRead) {
      deny(
        `Aegis is active — read ${result.path} via the aegis_read MCP tool instead of a shell ` +
          `command. Aegis classifies the file on-device and either passes it through, sanitizes ` +
          `PII, blocks credentials, or escalates to the user. See /aegis-status for current policy.`,
      );
    }
    process.exit(0); // not a simple read → allow
  }

  // Any other tool → allow.
  process.exit(0);
});
