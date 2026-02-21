// ============================================================================
// AEGIS_PATCH_FILE TOOL — Permanently redact line ranges in files
// ============================================================================

import fs from "fs";
import path from "path";
import type { DataGuardConfig } from "../types";
import { checkPath } from "../sanitize/policy";
import { log } from "../sanitize/audit";

export interface LineRange {
  start: number;  // 1-indexed line number
  end: number;    // 1-indexed line number (inclusive)
}

export interface DataguardPatchParams {
  path: string;
  ranges: LineRange[];
  reason: string;  // why this content is being redacted
}

export interface DataguardPatchResult {
  lines_redacted: number;
  backup_path: string;
}

/**
 * Create the dataguard_patch_file tool handler.
 * Permanently redacts specified line ranges by replacing them with a marker.
 * Creates a backup before modification.
 */
export function createDataguardPatchFile(config: DataGuardConfig) {
  return async function dataguardPatchFile(
    params: DataguardPatchParams
  ): Promise<DataguardPatchResult> {
    const absPath = path.resolve(params.path);

    // --- Step 1: Policy check ---
    const check = checkPath(params.path, config);
    if (check.verdict === "deny") {
      throw new Error(`Aegis denied: ${check.reason}`);
    }

    // --- Step 2: Read original file ---
    const original = fs.readFileSync(absPath, "utf-8");
    const lines = original.split("\n");

    // --- Step 3: Create backup ---
    const backupPath = `${absPath}.aegis-backup-${Date.now()}`;
    fs.writeFileSync(backupPath, original, "utf-8");

    // --- Step 4: Apply redactions ---
    let redacted = 0;
    for (const range of params.ranges) {
      for (let i = range.start - 1; i < Math.min(range.end, lines.length); i++) {
        lines[i] = `[REDACTED by Aegis: ${params.reason}]`;
        redacted++;
      }
    }

    // --- Step 5: Write back ---
    fs.writeFileSync(absPath, lines.join("\n"), "utf-8");

    // --- Step 6: Audit log ---
    log({
      timestamp: new Date().toISOString(),
      event: "aegis_patch_file",
      path: absPath,
      action: "patch",
      reason: params.reason,
      redactionCount: redacted,
    });

    return {
      lines_redacted: redacted,
      backup_path: backupPath,
    };
  };
}
