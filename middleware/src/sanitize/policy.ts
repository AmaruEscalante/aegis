// ============================================================================
// PATH & EGRESS POLICY ENFORCEMENT
// ============================================================================

import path from "path";
import { minimatch } from "minimatch";
import type { DataGuardConfig, PathCheckResult } from "../types";

/**
 * Check if a path is allowed to be accessed.
 * Verdict priority:
 *  1. Deny globs (highest) — .env, id_rsa, keychains, etc.
 *  2. Must be inside allowedRoots
 *  3. Sanitize-always globs (PDFs, docs, downloads)
 *  4. Default: sanitize everything else
 */
export function checkPath(rawPath: string, config: DataGuardConfig): PathCheckResult {
  const abs = path.resolve(rawPath);

  // 1. Check deny globs (highest priority)
  for (const glob of config.denyPathGlobs) {
    if (minimatch(abs, glob, { matchBase: true, dot: true })) {
      return {
        verdict: "deny",
        reason: `Path matches deny glob: ${glob}`,
      };
    }
  }

  // 2. Check if path is under an allowed root
  const inAllowedRoot = config.allowedRoots.some((root) => {
    const absRoot = path.resolve(root);
    return (
      abs.startsWith(absRoot + path.sep) ||
      abs === absRoot
    );
  });

  if (!inAllowedRoot) {
    return {
      verdict: "deny",
      reason: "Path not under any allowed root",
    };
  }

  // 3. Check sanitize-always globs (PDFs, docs, etc.)
  for (const glob of config.sanitizeAlwaysGlobs) {
    if (minimatch(abs, glob, { matchBase: true, dot: true })) {
      return {
        verdict: "sanitize",
        reason: `Matches sanitize-always glob: ${glob}`,
      };
    }
  }

  // 4. Default: sanitize all reads
  return {
    verdict: "sanitize",
    reason: "Default policy: sanitize all reads",
  };
}

/**
 * Check if a file size is within the allowed limit.
 */
export function checkFileSize(sizeBytes: number, config: DataGuardConfig): boolean {
  return sizeBytes <= config.maxFileBytes;
}

/**
 * Placeholder pattern: __CATEGORY_n__
 */
const PLACEHOLDER_REGEX = /__[A-Z_]+_\d+__/;

/**
 * Secret prefix patterns that indicate unencrypted secrets in payloads.
 */
const SECRET_PREFIX_REGEX = /\b(?:sk[-_][a-zA-Z0-9]{10,}|pk_(?:live|test)_[a-zA-Z0-9]{10,}|ghp_[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16})/;

/**
 * Check if a string payload contains sensitive data (placeholders or secrets).
 * Used to block egress tool calls that might leak redacted content.
 */
export function containsSensitiveData(payload: string): {
  found: boolean;
  reason?: string;
} {
  if (PLACEHOLDER_REGEX.test(payload)) {
    return {
      found: true,
      reason: "Payload contains unresolved placeholder token",
    };
  }

  if (SECRET_PREFIX_REGEX.test(payload)) {
    return {
      found: true,
      reason: "Payload contains secret-prefix token",
    };
  }

  return { found: false };
}
