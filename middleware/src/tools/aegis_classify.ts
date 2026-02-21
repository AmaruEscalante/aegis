// ============================================================================
// AEGIS_CLASSIFY TOOL — Standalone file classification via FunctionGemma
// ============================================================================
// Classifies a file's sensitivity without reading the full content back to
// the agent. Useful for pre-checking files before deciding how to handle them.

import fs from "fs";
import path from "path";
import type { DataGuardConfig, ClassifyResult } from "../types";
import { checkPath, checkFileSize } from "../sanitize/policy";
import { extractText } from "../sanitize/extract";
import { classifyFile } from "../router/classify";
import { log } from "../sanitize/audit";

export interface AegisClassifyParams {
  path: string;
}

/**
 * Create the aegis_classify tool handler.
 * Extracts text from a file, sends it through the Aegis bridge for
 * FunctionGemma classification, and returns the verdict.
 */
export function createAegisClassify(config: DataGuardConfig) {
  return async function aegisClassify(
    params: AegisClassifyParams
  ): Promise<ClassifyResult> {
    try {
      const rawPath = params.path;
      const absPath = path.resolve(rawPath);

      // --- Step 1: Policy check ---
      const check = checkPath(rawPath, config);
      if (check.verdict === "deny") {
        log({
          timestamp: new Date().toISOString(),
          event: "aegis_classify",
          path: absPath,
          action: "deny_path",
          reason: check.reason,
        });
        throw new Error(`Aegis denied access: ${check.reason}`);
      }

      // --- Step 2: File stat + size check ---
      const stat = fs.statSync(absPath);
      if (!checkFileSize(stat.size, config)) {
        throw new Error(
          `File too large: ${stat.size} bytes exceeds maxFileBytes ${config.maxFileBytes}`
        );
      }

      // --- Step 3: Extract text ---
      const extracted = await extractText(absPath, config.maxFileBytes);

      // --- Step 4: Classify via Aegis bridge ---
      const result = await classifyFile(extracted.text, config);

      // --- Step 5: Audit log ---
      log({
        timestamp: new Date().toISOString(),
        event: "aegis_classify",
        path: absPath,
        action: result.verdict === "safe" ? "classify_safe" :
               result.verdict === "block" ? "block_transfer" :
               result.verdict === "escalate" ? "escalate" : "sanitize",
        reason: result.reason,
      });

      return result;
    } catch (err) {
      console.error("[aegis_classify] ERROR:", err);
      throw err;
    }
  };
}
