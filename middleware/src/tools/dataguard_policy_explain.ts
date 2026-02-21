// ============================================================================
// AEGIS_POLICY_EXPLAIN TOOL — Explain current policy
// ============================================================================

import type { DataGuardConfig } from "../types";
import { size as vaultSize, listPlaceholders } from "../sanitize/vault";

export interface DataguardPolicyExplainResult {
  policy: {
    allowedRoots: string[];
    denyPathGlobs: string[];
    sanitizeAlwaysGlobs: string[];
    maxFileBytes: number;
    ollamaModel: string;
  };
  session: {
    vault_entries: number;
    placeholder_list: string[];
  };
  instructions: string[];
}

/**
 * Create the dataguard_policy_explain tool handler.
 * Returns current policy, session vault stats, and usage instructions.
 */
export function createDataguardPolicyExplain(config: DataGuardConfig) {
  return async function dataguardPolicyExplain(): Promise<DataguardPolicyExplainResult> {
    return {
      policy: {
        allowedRoots: config.allowedRoots,
        denyPathGlobs: config.denyPathGlobs,
        sanitizeAlwaysGlobs: config.sanitizeAlwaysGlobs,
        maxFileBytes: config.maxFileBytes,
        ollamaModel: config.ollamaModel,
      },
      session: {
        vault_entries: vaultSize(),
        placeholder_list: listPlaceholders(),
      },
      instructions: [
        "Use aegis_read({path}) to read any file safely (classifies first, then sanitizes if needed).",
        "Use aegis_search({query, root}) to search file contents and get sanitized snippets.",
        "Use aegis_classify({path}) to check a file's sensitivity without reading its content.",
        "Use aegis_patch_file({path, ranges, reason}) to permanently redact line ranges.",
        "Use aegis_sanitize_path({path}) to force re-sanitization and refresh cache.",
        "Native file tools (Read, Glob, Grep, fs.*) are BLOCKED.",
        "Egress tools (http, fetch, curl) are BLOCKED if payload contains secrets or placeholders.",
        "All secrets/PII are replaced with __CATEGORY_n__ placeholders that are impossible to rehydrate externally.",
      ],
    };
  };
}
