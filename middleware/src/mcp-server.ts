// ============================================================================
// AEGIS MCP SERVER
// ============================================================================
// Wraps the Aegis middleware tools as an MCP (Model Context Protocol) server.
// Any MCP-compatible agent (Claude Desktop, Claude Code, Cursor, etc.) can
// connect and use aegis_read, aegis_classify, and aegis_policy_explain as tools.
//
// Usage:
//   npx tsx src/mcp-server.ts
//   node dist/mcp-server.js
//
// The bridge must be running:
//   uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter

import os from "os";
import path from "path";
import fs from "fs";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import type { DataGuardConfig } from "./types";
import { initAudit } from "./sanitize/audit";
import { initCache } from "./sanitize/cache";
import { createDataguardRead } from "./tools/dataguard_read";
import { createAegisClassify } from "./tools/aegis_classify";
import { createDataguardPolicyExplain } from "./tools/dataguard_policy_explain";
import { createDataguardSanitizePath } from "./tools/dataguard_sanitize_path";
import { healthCheck } from "./router/classify";

// ---- Configuration --------------------------------------------------------

const DEFAULT_CONFIG: DataGuardConfig = {
  denyPathGlobs: [
    "**/.env", "**/.env.*", "**/id_rsa*", "**/id_ed25519*",
    "**/*.pem", "**/*.p12", "**/*.pfx", "**/keychain/**",
    "**/Keychain/**", "**/.ssh/**",
    "**/Library/Application Support/Google/Chrome/**",
    "**/Library/Application Support/Firefox/**",
  ],
  allowedRoots: [process.cwd(), path.resolve(process.cwd(), "..")],
  sanitizeAlwaysGlobs: ["**/*.pdf", "**/*.docx", "**/*.doc", "**/docs/**", "**/downloads/**", "**/Downloads/**"],
  maxFileBytes: 5 * 1024 * 1024,
  cacheDir: path.join(os.homedir(), ".openclaw", "aegis", "cache"),
  auditLogPath: path.join(os.homedir(), ".openclaw", "aegis", "audit.jsonl"),
  llmProvider: "ollama",
  ollamaBaseUrl: "http://127.0.0.1:11434",
  ollamaModel: "gemma2:latest",
  ollamaTimeoutMs: 30_000,
  openrouterApiKey: "",
  openrouterModel: "qwen/qwen3-coder",
  openrouterTimeoutMs: 60_000,
  llmMode: "tool-calling",
  aegisEnabled: true,
  aegisBridgeUrl: "http://127.0.0.1:7523",
  aegisBridgeTimeoutMs: 15_000,
};

/**
 * Load configuration from ~/.openclaw/openclaw.json, merged with defaults.
 */
function loadConfig(): DataGuardConfig {
  const configFile = path.join(os.homedir(), ".openclaw", "openclaw.json");
  try {
    const raw = JSON.parse(fs.readFileSync(configFile, "utf-8"));
    const pluginConfig =
      raw?.plugins?.entries?.aegis?.config ??
      raw?.plugins?.entries?.dataguard?.config ??
      {};
    return {
      ...DEFAULT_CONFIG,
      ...pluginConfig,
      denyPathGlobs: pluginConfig.denyPathGlobs ?? DEFAULT_CONFIG.denyPathGlobs,
      allowedRoots: pluginConfig.allowedRoots ?? DEFAULT_CONFIG.allowedRoots,
      sanitizeAlwaysGlobs: pluginConfig.sanitizeAlwaysGlobs ?? DEFAULT_CONFIG.sanitizeAlwaysGlobs,
    };
  } catch {
    return DEFAULT_CONFIG;
  }
}

// ---- Main -----------------------------------------------------------------

async function main() {
  const config = loadConfig();

  // Initialize subsystems
  initAudit(config.auditLogPath);
  initCache(config.cacheDir);

  // Create tool handlers
  const aegisRead = createDataguardRead(config);
  const aegisClassify = createAegisClassify(config);
  const aegisPolicyExplain = createDataguardPolicyExplain(config);
  const aegisSanitizePath = createDataguardSanitizePath(config);

  // Check bridge health
  const health = await healthCheck(config);
  if (health.status === "ok") {
    console.error(`[aegis-mcp] Bridge connected: backend=${health.backend}, model=${health.model}`);
  } else {
    console.error("[aegis-mcp] Bridge unreachable — will fall back to sanitize-everything mode");
    console.error("[aegis-mcp] Start it with: uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter");
  }

  // Create MCP server
  const server = new McpServer({
    name: "aegis",
    version: "2.0.0",
  });

  // ---- aegis_read ----
  server.tool(
    "aegis_read",
    "Read a file through the Aegis privacy router. Classifies content on-device via FunctionGemma, " +
    "then either passes through (safe), sanitizes PII (flag_pii), blocks (secrets), or " +
    "escalates (ambiguous content needing human review). Use this instead of reading files directly.",
    {
      path: z.string().describe("Absolute or relative path to the file to read"),
      mode: z.enum(["full", "summary"]).optional().describe("full = return all content (default), summary = first 2000 chars only"),
    },
    async ({ path: filePath, mode }) => {
      try {
        const result = await aegisRead({ path: filePath, mode: mode as "full" | "summary" | undefined });

        // Handle escalation — return the escalation message
        if (result.method === "aegis-escalate" && "escalation" in result) {
          const esc = (result as any).escalation;
          return {
            content: [
              {
                type: "text" as const,
                text: JSON.stringify({
                  aegis_verdict: "escalate",
                  method: "aegis-escalate",
                  escalation: esc,
                }, null, 2),
              },
            ],
          };
        }

        // Normal result (safe, flag_pii sanitized)
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                aegis_verdict: (result as any).aegis_verdict ?? "flag_pii",
                method: result.method,
                redaction_count: result.redaction_count,
                format: ("format" in result) ? (result as any).format : undefined,
                cached: result.cached,
                sanitized_text: ("sanitized_text" in result) ? (result as any).sanitized_text : undefined,
              }, null, 2),
            },
          ],
        };
      } catch (err: any) {
        // Block verdicts throw an error — return it as an error result
        return {
          content: [
            {
              type: "text" as const,
              text: err.message ?? String(err),
            },
          ],
          isError: true,
        };
      }
    },
  );

  // ---- aegis_classify ----
  server.tool(
    "aegis_classify",
    "Classify a file's sensitivity using on-device FunctionGemma without reading its full content. " +
    "Returns verdict (safe/flag_pii/block/escalate), confidence, and reason. " +
    "Useful for checking a file before deciding how to handle it.",
    {
      path: z.string().describe("Path to the file to classify"),
    },
    async ({ path: filePath }) => {
      try {
        const result = await aegisClassify({ path: filePath });
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (err: any) {
        return {
          content: [{ type: "text" as const, text: err.message ?? String(err) }],
          isError: true,
        };
      }
    },
  );

  // ---- aegis_sanitize_path ----
  server.tool(
    "aegis_sanitize_path",
    "Force re-sanitization of a file (bypasses cache). Runs the full DataGuard pipeline " +
    "(regex + LLM detection) and returns the redaction count and method.",
    {
      path: z.string().describe("Path to the file to sanitize"),
    },
    async ({ path: filePath }) => {
      try {
        const result = await aegisSanitizePath({ path: filePath });
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (err: any) {
        return {
          content: [{ type: "text" as const, text: err.message ?? String(err) }],
          isError: true,
        };
      }
    },
  );

  // ---- aegis_policy_explain ----
  server.tool(
    "aegis_policy_explain",
    "Returns the current Aegis security policy, session vault stats, and usage instructions.",
    {},
    async () => {
      const result = await aegisPolicyExplain();
      return {
        content: [
          {
            type: "text" as const,
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    },
  );

  // Connect via stdio transport
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[aegis-mcp] Server running on stdio");
}

main().catch((err) => {
  console.error("[aegis-mcp] Fatal error:", err);
  process.exit(1);
});
