// ============================================================================
// BEFORE_TOOL_CALL HOOK — Block native file access and egress leaks (Aegis)
// ============================================================================

import type { BeforeToolCallContext, BeforeToolCallResult, DataGuardConfig } from "../types";
import { containsSensitiveData } from "../sanitize/policy";
import { log } from "../sanitize/audit";

/**
 * Tools that read/search the filesystem.
 * The agent must use aegis_* tools instead.
 * (Case-insensitive matching)
 */
const BLOCKED_READ_TOOLS = new Set([
  // OpenClaw / Claude Code native
  "fs.read",
  "fs.search",
  "fs.list",
  "fs.glob",
  "fs.stat",
  "fs.read_binary",
  // Claude Code tools (Explore agent)
  "read",
  "glob",
  "grep",
  "ls",
  "find",
  // Common aliases
  "readfile",
  "file_read",
  "cat",
  "head",
  "tail",
]);

/**
 * Tools that send data externally.
 * Must be inspected for secrets/placeholders before allowing.
 * (Case-insensitive matching)
 */
const EGRESS_TOOLS = new Set([
  "http",
  "curl",
  "fetch",
  "exec",
  "shell",
  "bash",
  "web_search",
  "browser",
  "http_request",
  "message",
  "send",
  "post",
  "get",
]);

/**
 * Check if a tool name matches the blocked read tools set.
 */
function isBlockedReadTool(toolName: string): boolean {
  return BLOCKED_READ_TOOLS.has(toolName.toLowerCase());
}

/**
 * Check if a tool name matches the egress tools set.
 */
function isEgressTool(toolName: string): boolean {
  return EGRESS_TOOLS.has(toolName.toLowerCase());
}

/**
 * Serialize params to a string for sensitive data inspection.
 */
function paramsToString(params: Record<string, unknown>): string {
  try {
    return JSON.stringify(params);
  } catch {
    return String(params);
  }
}

/**
 * Create the before_tool_call hook handler.
 * Returns a function that checks tool calls and blocks as needed.
 */
export function createBeforeToolCallHandler(
  config: DataGuardConfig
) {
  return function handleBeforeToolCall(
    ctx: BeforeToolCallContext
  ): BeforeToolCallResult {
    try {
      const { toolName, params } = ctx;

    // --- Block 1: Native file-access tools ---
    if (isBlockedReadTool(toolName)) {
      log({
        timestamp: new Date().toISOString(),
        event: "before_tool_call",
        toolName,
        action: "block",
        reason:
          "Use aegis_read / aegis_search instead of native file tools",
      });

      return {
        block: true,
        blockReason:
          `Tool '${toolName}' is blocked by Aegis. ` +
          `Use aegis_read({path}) or aegis_search({query, root}) to access files safely. ` +
          `Use aegis_policy_explain() to understand current policy.`,
      };
    }

    // --- Block 2: Egress tools with sensitive payloads ---
    if (isEgressTool(toolName)) {
      const payload = paramsToString(params);
      const check = containsSensitiveData(payload);

      if (check.found) {
        log({
          timestamp: new Date().toISOString(),
          event: "before_tool_call",
          toolName,
          action: "egress_blocked",
          reason: check.reason,
        });

        return {
          block: true,
          blockReason:
            `Egress blocked by Aegis: ${check.reason}. ` +
            `Never send placeholders or secrets externally. ` +
            `Use only sanitized content in external calls.`,
        };
      }
    }

    // --- Allow: no issues found ---
    return {};
    } catch (err) {
      console.error("[before_tool_call] ERROR:", err);
      throw err;
    }
  };
}
