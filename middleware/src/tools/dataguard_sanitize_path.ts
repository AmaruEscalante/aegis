// ============================================================================
// AEGIS_SANITIZE_PATH TOOL — Force re-sanitization of a file
// ============================================================================

import fs from "fs";
import path from "path";
import type { DataGuardConfig } from "../types";
import { checkPath } from "../sanitize/policy";
import { extractText } from "../sanitize/extract";
import { sanitize } from "../sanitize/sanitize";
import { set as cacheSet } from "../sanitize/cache";
import { log } from "../sanitize/audit";

export interface DataguardSanitizePathParams {
  path: string;
}

export interface DataguardSanitizePathResult {
  sanitized_path: string;
  redaction_count: number;
  method: string;
  summary: string;
}

/**
 * Create the dataguard_sanitize_path tool handler.
 * Forces re-sanitization of a file (bypasses cache read, writes new cache entry).
 * Useful when you want to refresh the sanitized version.
 */
export function createDataguardSanitizePath(config: DataGuardConfig) {
  return async function dataguardSanitizePath(
    params: DataguardSanitizePathParams
  ): Promise<DataguardSanitizePathResult> {
    const absPath = path.resolve(params.path);

    // --- Step 1: Policy check ---
    const check = checkPath(params.path, config);
    if (check.verdict === "deny") {
      throw new Error(`Denied: ${check.reason}`);
    }

    // --- Step 2: Stat file ---
    const stat = fs.statSync(absPath);
    const cacheKey = {
      absolutePath: absPath,
      mtime: stat.mtimeMs,
      size: stat.size,
    };

    // --- Step 3: Extract text ---
    const extracted = await extractText(absPath, config.maxFileBytes);

    // --- Step 4: Sanitize (force, ignore cache) ---
    const result = await sanitize(extracted.text, config);

    // --- Step 5: Update cache ---
    cacheSet(cacheKey, {
      sanitizedText: result.sanitized_text,
      redactions: result.redactions,
      method: result.method,
      cachedAt: Date.now(),
    });

    // --- Step 6: Audit log ---
    log({
      timestamp: new Date().toISOString(),
      event: "aegis_sanitize_path",
      path: absPath,
      action: "sanitize",
      redactionCount: result.redactions.length,
    });

    return {
      sanitized_path: absPath,
      redaction_count: result.redactions.length,
      method: result.method,
      summary:
        result.llm_summary ?? `${result.redactions.length} items redacted`,
    };
  };
}
