// ============================================================================
// AUDIT LOGGING — JSONL APPEND-ONLY LOG
// ============================================================================

import fs from "fs";
import path from "path";
import type { AuditEvent } from "../types";

/**
 * Path to the audit log file.
 * Set by initAudit().
 */
let auditFilePath: string | null = null;

/**
 * Initialize the audit log by setting the target file path.
 * Creates parent directories if needed.
 */
export function initAudit(filePath: string): void {
  auditFilePath = filePath;
  // Ensure parent directory exists
  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
  } catch {
    // Directory may already exist or permission denied — non-fatal
  }
}

/**
 * Log an audit event as a JSON line.
 * Best-effort: errors are silently ignored to prevent blocking tool execution.
 */
export function log(event: AuditEvent): void {
  if (!auditFilePath) return; // Audit not initialized

  const entry = {
    ...event,
    timestamp: new Date().toISOString(),  // Override any timestamp in event
  };

  const line = JSON.stringify(entry) + "\n";

  try {
    fs.appendFileSync(auditFilePath, line, "utf-8");
  } catch {
    // Non-fatal: never throw from audit logging
    // (this could break tool execution if filesystem is having issues)
  }
}

/**
 * Read all audit log entries (for debugging/analytics).
 * Skips malformed lines silently.
 */
export function readLog(): AuditEvent[] {
  if (!auditFilePath || !fs.existsSync(auditFilePath)) return [];

  const content = fs.readFileSync(auditFilePath, "utf-8");
  const entries: AuditEvent[] = [];

  for (const line of content.split("\n")) {
    if (!line.trim()) continue;
    try {
      entries.push(JSON.parse(line) as AuditEvent);
    } catch {
      // Skip malformed lines
    }
  }

  return entries;
}
