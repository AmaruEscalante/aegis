// ============================================================================
// AEGIS_READ TOOL — Smart file reading with Aegis classification + DataGuard sanitization
// ============================================================================
// Pipeline:
//   Step 0: Aegis classification (FunctionGemma via bridge)
//     safe     → return raw text (no PII processing)
//     flag_pii → DataGuard sanitization pipeline (Steps 3-8)
//     block    → deny with explanation
//     escalate → return structured escalation to agent
//   Steps 1-8: Original DataGuard pipeline (policy, extract, sanitize, cache, audit)

import fs from "fs";
import path from "path";
import type { DataGuardConfig, AegisReadResult } from "../types";
import { checkPath, checkFileSize } from "../sanitize/policy";
import { extractText } from "../sanitize/extract";
import { sanitize } from "../sanitize/sanitize";
import { redactPdfWithLlmAnalysis } from "../sanitize/pdf-redactor";
import { redactFileWithLlmAnalysis } from "../sanitize/file-redactor";
import {
  get as cacheGet,
  set as cacheSet,
  getPdfRedact,
  setPdfRedact,
} from "../sanitize/cache";
import { log } from "../sanitize/audit";
import { classifyFile } from "../router/classify";

export interface DataguardReadParams {
  path: string;
  mode?: "full" | "summary";  // summary: first 2000 chars
}

export interface DataguardReadResult {
  sanitized_text: string;
  sanitized_path: string;
  format: string;
  redaction_count: number;
  method: string;  // "llm+regex", "regex-only", "aegis-safe", "aegis-blocked", "aegis-escalate"
  cached: boolean;
  redacted_file_path?: string;
  aegis_verdict?: string;
  aegis_confidence?: number;
  escalation?: {
    reason: string;
    confidence: number;
    message: string;
  };
}

/**
 * Create the aegis_read tool handler.
 * When Aegis is enabled, classifies files first via FunctionGemma.
 * Falls back to sanitize-everything if the bridge is unavailable.
 */
export function createDataguardRead(config: DataGuardConfig) {
  return async function aegisRead(
    params: DataguardReadParams
  ): Promise<DataguardReadResult | AegisReadResult> {
    try {
      const rawPath = params.path;
      const absPath = path.resolve(rawPath);

    // --- Step 1: Policy check ---
    const check = checkPath(rawPath, config);
    if (check.verdict === "deny") {
      log({
        timestamp: new Date().toISOString(),
        event: "aegis_read",
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

    // --- Step 0: Aegis classification (FunctionGemma via bridge) ---
    // Runs BEFORE cache check so classification informs the action.
    // Extracts text early since we need it for both classification and sanitization.
    const extracted = await extractText(absPath, config.maxFileBytes);

    if (config.aegisEnabled) {
      const classification = await classifyFile(extracted.text, config);

      // ---- Route: SAFE — return raw text, no sanitization needed ----
      if (classification.verdict === "safe") {
        log({
          timestamp: new Date().toISOString(),
          event: "aegis_read",
          path: absPath,
          action: "classify_safe",
          reason: classification.reason,
        });

        const text =
          params.mode === "summary"
            ? extracted.text.slice(0, 2000)
            : extracted.text;

        return {
          sanitized_text: text,
          sanitized_path: absPath,
          format: extracted.format,
          redaction_count: 0,
          method: "aegis-safe",
          cached: false,
          aegis_verdict: "safe",
          aegis_confidence: classification.confidence,
        };
      }

      // ---- Route: BLOCK — deny content based on classification ----
      if (classification.verdict === "block") {
        log({
          timestamp: new Date().toISOString(),
          event: "aegis_read",
          path: absPath,
          action: "block_transfer",
          reason: classification.reason,
        });

        throw new Error(
          `Aegis blocked file: ${classification.reason}. ` +
          `This file contains secrets or credentials and must not be shared.`
        );
      }

      // ---- Route: ESCALATE — return structured escalation to agent ----
      if (classification.verdict === "escalate") {
        log({
          timestamp: new Date().toISOString(),
          event: "aegis_read",
          path: absPath,
          action: "escalate",
          reason: classification.reason,
        });

        return {
          content: null,
          format: extracted.format,
          aegis_verdict: "escalate",
          aegis_reason: classification.reason,
          aegis_confidence: classification.confidence,
          redaction_count: 0,
          method: "aegis-escalate",
          cached: false,
          escalation: {
            reason: classification.reason,
            confidence: classification.confidence,
            message:
              "This file requires human review before it can be shared. " +
              `Reason: ${classification.reason}. ` +
              "Please ask the user for explicit permission before proceeding.",
          },
        };
      }

      // ---- Route: FLAG_PII — fall through to DataGuard sanitization pipeline ----
      // classification.verdict === "flag_pii" — continue to Steps 3-8 below
    }

    // --- Step 3: Check cache ---
    const cacheKey = {
      absolutePath: absPath,
      mtime: stat.mtimeMs,
      size: stat.size,
    };

    const cached = cacheGet(cacheKey);
    if (cached) {
      log({
        timestamp: new Date().toISOString(),
        event: "aegis_read",
        path: absPath,
        action: "cache_hit",
        redactionCount: cached.redactions ? cached.redactions.length : 0,
      });

      const text =
        params.mode === "summary"
          ? cached.sanitizedText.slice(0, 2000)
          : cached.sanitizedText;

      const redactionCount = Array.isArray(cached.redactions) ? cached.redactions.length : 0;

      // Return minimal object - avoid any potential circular references
      return JSON.parse(JSON.stringify({
        sanitized_text: text,
        sanitized_path: absPath,
        format: "cached",
        redaction_count: redactionCount,
        method: cached.method || "unknown",
        cached: true,
        aegis_verdict: "flag_pii",
      }));
    }

    // --- Step 5a: File redaction (PDF visual patches OR text redaction for all formats) ---
    let redactedFilePath: string | undefined;

    try {
      const redactCacheKey = {
        absolutePath: absPath,
        mtime: stat.mtimeMs,
        size: stat.size,
      };

      // For PDFs: visual black patches
      if (extracted.format === "pdf") {
        const pdfCached = getPdfRedact(redactCacheKey);
        if (pdfCached) {
          redactedFilePath = pdfCached.redactedPdfPath;
          log({
            timestamp: new Date().toISOString(),
            event: "aegis_read",
            path: absPath,
            action: "cache_hit",
            reason: "file-redact cache hit (PDF)",
          });
        } else {
          const pdfResult = await redactPdfWithLlmAnalysis(
            absPath,
            extracted.text,
            config
          );
          redactedFilePath = pdfResult.redactedPdfPath;
          setPdfRedact(redactCacheKey, {
            redactedPdfPath: pdfResult.redactedPdfPath,
            redactionCount: pdfResult.redactionCount,
            method: pdfResult.method,
            cachedAt: Date.now(),
          });
        }
      } else {
        // For all other formats: intelligent text redaction
        const fileResult = await redactFileWithLlmAnalysis(
          absPath,
          extracted.text,
          config
        );
        redactedFilePath = fileResult.redactedFilePath;
      }
    } catch (err) {
      // File redaction failure is non-fatal; text sanitization still runs
      log({
        timestamp: new Date().toISOString(),
        event: "aegis_read",
        path: absPath,
        action: "sanitize",
        reason: `File redaction failed (non-fatal): ${err}`,
      });
    }

    // --- Step 5b: Text sanitization (all formats) ---
    const result = await sanitize(extracted.text, config);

    // --- Step 6: Cache the sanitized text result ---
    cacheSet(cacheKey, {
      sanitizedText: result.sanitized_text,
      redactions: result.redactions,
      method: result.method,
      cachedAt: Date.now(),
    });

    // --- Step 7: Audit log ---
    log({
      timestamp: new Date().toISOString(),
      event: "aegis_read",
      path: absPath,
      action: "sanitize",
      redactionCount: result.redactions.length,
      method: result.method,
    });

    // --- Step 8: Return result ---
    const text =
      params.mode === "summary"
        ? result.sanitized_text.slice(0, 2000)
        : result.sanitized_text;

    return {
      sanitized_text: text,
      sanitized_path: absPath,
      format: extracted.format,
      redaction_count: result.redactions.length,
      method: result.method,
      cached: false,
      redacted_file_path: redactedFilePath,
      aegis_verdict: "flag_pii",
    };
    } catch (err) {
      console.error("[aegis_read] ERROR:", err);
      throw err;
    }
  };
}
