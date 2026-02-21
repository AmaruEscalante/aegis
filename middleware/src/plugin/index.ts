// ============================================================================
// AEGIS PLUGIN ENTRY POINT
// ============================================================================
// Registers the Aegis privacy router with OpenClaw: hooks + tools.
// Aegis classifies files via FunctionGemma (on-device) before deciding
// whether to pass through, sanitize (DataGuard), block, or escalate.
// MUST be synchronous (OpenClaw requirement).

import os from "os";
import path from "path";
import fs from "fs";
import type { DataGuardConfig, BeforeToolCallContext, OpenClawPluginApi } from "../types";
import { initAudit } from "../sanitize/audit";
import { initCache } from "../sanitize/cache";
import { createBeforeToolCallHandler } from "../hooks/before_tool_call";
import { createDataguardRead } from "../tools/dataguard_read";
import { createDataguardSearch } from "../tools/dataguard_search";
import { createDataguardPatchFile } from "../tools/dataguard_patch_file";
import { createDataguardSanitizePath } from "../tools/dataguard_sanitize_path";
import { createDataguardPolicyExplain } from "../tools/dataguard_policy_explain";
import { createAegisClassify } from "../tools/aegis_classify";
import { healthCheck } from "../router/classify";

/**
 * Default configuration for Aegis plugin.
 * Loaded from ~/.openclaw/openclaw.json, merged with these defaults.
 */
const DEFAULT_CONFIG: DataGuardConfig = {
  // Paths that are absolutely forbidden to access
  denyPathGlobs: [
    "**/.env",
    "**/.env.*",
    "**/id_rsa*",
    "**/id_ed25519*",
    "**/*.pem",
    "**/*.p12",
    "**/*.pfx",
    "**/keychain/**",
    "**/Keychain/**",
    "**/Library/Application Support/Google/Chrome/**",
    "**/Library/Application Support/Firefox/**",
    "**/.ssh/**",
  ],

  // Only allow access under these directories
  allowedRoots: [process.cwd()],

  // Always sanitize files matching these globs (PDFs, docs, etc.)
  sanitizeAlwaysGlobs: [
    "**/*.pdf",
    "**/*.docx",
    "**/*.doc",
    "**/docs/**",
    "**/downloads/**",
    "**/Downloads/**",
  ],

  // Maximum file size to process (5 MB default)
  maxFileBytes: 5 * 1024 * 1024,

  // Cache directory for sanitized artifacts
  cacheDir: path.join(os.homedir(), ".openclaw", "aegis", "cache"),

  // Audit log path
  auditLogPath: path.join(os.homedir(), ".openclaw", "aegis", "audit.jsonl"),

  // LLM Provider: "ollama" (default, local) or "openrouter" (cloud)
  llmProvider: "ollama",

  // Ollama endpoint (must be localhost only)
  ollamaBaseUrl: "http://127.0.0.1:11434",

  // Ollama model to use for sanitization
  ollamaModel: "gemma2:latest",

  // Timeout for Ollama requests (milliseconds)
  ollamaTimeoutMs: 30_000,

  // OpenRouter API key (get from https://openrouter.ai)
  openrouterApiKey: "",

  // OpenRouter model
  openrouterModel: "qwen/qwen3-coder",

  // Timeout for OpenRouter requests (milliseconds)
  openrouterTimeoutMs: 60_000,

  // LLM redaction mode: "tool-calling" (surgical edits) or "prompt" (full rewrite)
  llmMode: "tool-calling",

  // Aegis Router (FunctionGemma classification bridge)
  aegisEnabled: true,
  aegisBridgeUrl: "http://127.0.0.1:7523",
  aegisBridgeTimeoutMs: 10_000,
};

/**
 * Load configuration from ~/.openclaw/openclaw.json
 * Checks both "aegis" and "dataguard" plugin entries for backwards compatibility.
 */
function loadConfig(): DataGuardConfig {
  const configFile = path.join(os.homedir(), ".openclaw", "openclaw.json");

  try {
    const raw = JSON.parse(fs.readFileSync(configFile, "utf-8"));
    // Check aegis first, fall back to dataguard for migration
    const pluginConfig =
      raw?.plugins?.entries?.aegis?.config ??
      raw?.plugins?.entries?.dataguard?.config ??
      {};

    // Deep merge with defaults
    return {
      ...DEFAULT_CONFIG,
      ...pluginConfig,
      // Array fields: use from config if present, else defaults
      denyPathGlobs:
        pluginConfig.denyPathGlobs ?? DEFAULT_CONFIG.denyPathGlobs,
      allowedRoots: pluginConfig.allowedRoots ?? DEFAULT_CONFIG.allowedRoots,
      sanitizeAlwaysGlobs:
        pluginConfig.sanitizeAlwaysGlobs ??
        DEFAULT_CONFIG.sanitizeAlwaysGlobs,
    };
  } catch {
    // Config file not found or invalid JSON — use defaults
    return DEFAULT_CONFIG;
  }
}

/**
 * The Aegis plugin object.
 * Exported as default; loaded by OpenClaw at startup.
 */
const plugin = {
  id: "aegis",
  name: "Aegis",

  /**
   * Register the plugin with OpenClaw.
   * MUST be synchronous (OpenClaw requirement).
   *
   * Initializes:
   *  1. Config loading
   *  2. Audit log and cache subsystems
   *  3. before_tool_call hook
   *  4. Six aegis_* tools
   *  5. Non-blocking bridge health check
   */
  register(api: OpenClawPluginApi): void {
    // Load configuration
    const config = loadConfig();

    // Initialize subsystems
    initAudit(config.auditLogPath);
    initCache(config.cacheDir);

    // Create and register the before_tool_call hook
    const hookHandler = createBeforeToolCallHandler(config);

    if (api.on) {
      api.on("before_tool_call", (ctx: unknown) => {
        return hookHandler(ctx as BeforeToolCallContext);
      });
    }

    // Create tool handlers
    const readTool = createDataguardRead(config);
    const searchTool = createDataguardSearch(config);
    const patchTool = createDataguardPatchFile(config);
    const sanitizeTool = createDataguardSanitizePath(config);
    const policyTool = createDataguardPolicyExplain(config);
    const classifyTool = createAegisClassify(config);

    // Register tools with OpenClaw
    if (api.registerTool) {
      // --- aegis_read ---
      api.registerTool({
        name: "aegis_read",
        description:
          "Reads a file through the Aegis privacy router. Classifies content via FunctionGemma, " +
          "then either passes through (safe), sanitizes PII (flag_pii), blocks (secrets), or " +
          "escalates (ambiguous). Use instead of Read/Glob.",
        parameters: {
          type: "object",
          properties: {
            path: {
              type: "string",
              description: "Absolute or relative path to the file to read",
            },
            mode: {
              type: "string",
              enum: ["full", "summary"],
              description:
                'full=return all content, summary=first 2000 chars only',
            },
          },
          required: ["path"],
        },
        execute: async (...args: unknown[]) =>
          readTool(args[1] as any),
      });

      // --- aegis_search ---
      api.registerTool({
        name: "aegis_search",
        description:
          "Search files under a directory, return sanitized matching snippets (NOT raw files).",
        parameters: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Search query (regex or literal string)",
            },
            root: {
              type: "string",
              description: "Root directory to search under",
            },
            maxResults: {
              type: "number",
              description: "Maximum number of results to return (default 20)",
            },
          },
          required: ["query", "root"],
        },
        execute: async (...args: unknown[]) =>
          searchTool(args[1] as any),
      });

      // --- aegis_classify ---
      api.registerTool({
        name: "aegis_classify",
        description:
          "Classify a file's sensitivity using FunctionGemma (on-device). Returns verdict " +
          "(safe/flag_pii/block/escalate) without reading the full file content. " +
          "Useful for checking a file before deciding how to handle it.",
        parameters: {
          type: "object",
          properties: {
            path: {
              type: "string",
              description: "Path to the file to classify",
            },
          },
          required: ["path"],
        },
        execute: async (...args: unknown[]) =>
          classifyTool(args[1] as any),
      });

      // --- aegis_patch_file ---
      api.registerTool({
        name: "aegis_patch_file",
        description:
          "Permanently redact specified line ranges in a file. Creates a backup before modification.",
        parameters: {
          type: "object",
          properties: {
            path: {
              type: "string",
              description: "Path to file to redact",
            },
            ranges: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  start: {
                    type: "number",
                    description: "1-indexed start line number (inclusive)",
                  },
                  end: {
                    type: "number",
                    description: "1-indexed end line number (inclusive)",
                  },
                },
                required: ["start", "end"],
              },
              description: "Array of line ranges to redact",
            },
            reason: {
              type: "string",
              description: "Why this content is being redacted (e.g. 'contains customer SSN')",
            },
          },
          required: ["path", "ranges", "reason"],
        },
        execute: async (...args: unknown[]) =>
          patchTool(args[1] as any),
      });

      // --- aegis_sanitize_path ---
      api.registerTool({
        name: "aegis_sanitize_path",
        description:
          "Force re-sanitization of a file (bypasses cache). Returns redaction count and summary.",
        parameters: {
          type: "object",
          properties: {
            path: {
              type: "string",
              description: "Path to file to sanitize",
            },
          },
          required: ["path"],
        },
        execute: async (...args: unknown[]) =>
          sanitizeTool(args[1] as any),
      });

      // --- aegis_policy_explain ---
      api.registerTool({
        name: "aegis_policy_explain",
        description:
          "Returns current Aegis policy, session vault stats, and instructions.",
        parameters: {
          type: "object",
          properties: {},
        },
        execute: async (...args: unknown[]) => policyTool(),
      });
    }

    // Non-blocking bridge health check at startup
    if (config.aegisEnabled) {
      healthCheck(config).then((health) => {
        if (health.status === "ok") {
          console.log(
            `[aegis] Bridge connected: backend=${health.backend}, model=${health.model}`
          );
        } else {
          console.warn(
            "[aegis] Bridge unreachable — will fall back to sanitize-everything mode"
          );
        }
      });
    } else {
      console.log("[aegis] Router disabled (aegisEnabled=false) — sanitize-everything mode");
    }
  },
};

export default plugin;
