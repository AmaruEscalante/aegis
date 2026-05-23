#!/usr/bin/env node
/**
 * Aegis PreToolUse hook — reject Read/Glob/Grep calls and route Claude
 * to use the aegis_read MCP tool instead.
 *
 * Claude Code hooks receive a JSON payload on stdin describing the tool
 * call. We emit JSON on stdout with `decision: "block"` and a message
 * Claude can read to self-correct.
 *
 * Protocol reference: https://docs.claude.com/claude-code/hooks
 */

const BLOCKED = new Set(['Read', 'Glob', 'Grep']);

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { raw += chunk; });
process.stdin.on('end', () => {
    let payload;
    try {
        payload = JSON.parse(raw);
    } catch (e) {
        // If we can't parse, fail open (let the call through) so we
        // don't accidentally brick Claude Code. Log to stderr for debugging.
        console.error(`[aegis-hook] failed to parse hook payload: ${e.message}`);
        process.exit(0);
    }

    const toolName = payload?.tool_name;
    if (!BLOCKED.has(toolName)) {
        // Not a tool we care about — allow.
        process.exit(0);
    }

    // Block with a clear redirect message Claude can act on.
    const response = {
        decision: 'block',
        reason: `Aegis is active — use aegis_read instead of ${toolName} for file content. ` +
                `Aegis classifies the file on-device and either passes it through, sanitizes PII, ` +
                `blocks credentials, or escalates to the user. See /aegis-status for current policy.`,
    };
    process.stdout.write(JSON.stringify(response) + '\n');
    process.exit(0);
});
