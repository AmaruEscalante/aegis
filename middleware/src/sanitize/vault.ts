// ============================================================================
// IN-MEMORY VAULT FOR PLACEHOLDER → ORIGINAL MAPPINGS
// ============================================================================
// Stores secrets/PII mapped to placeholders during session.
// CRITICAL: never serialized to disk, never fully exposed to LLM.

import type { VaultEntry, PiiCategory } from "../types";

/**
 * Singleton in-memory store of placeholder → original value mappings.
 * Scoped to a single OpenClaw session (plugin lifetime).
 */
const store = new Map<string, VaultEntry>();

/**
 * Add mappings from detections to the vault.
 * Called after sanitization pass.
 */
export function addMappings(detections: Array<{
  placeholder: string;
  original: string;
  category: PiiCategory;
}>): void {
  const now = Date.now();
  for (const d of detections) {
    store.set(d.placeholder, {
      placeholder: d.placeholder,
      original: d.original,
      category: d.category,
      addedAt: now,
    });
  }
}

/**
 * Look up a placeholder to get its vault entry.
 * Does NOT return the original value — only metadata.
 */
export function lookup(placeholder: string): VaultEntry | undefined {
  return store.get(placeholder);
}

/**
 * Resolve a placeholder to its original value.
 * INTERNAL USE ONLY — only called from dataguard_patch_file
 * to write real bytes back to the file.
 * NEVER called from code paths that return to LLM.
 */
export function resolve(placeholder: string): string | undefined {
  return store.get(placeholder)?.original;
}

/**
 * Return count of entries in vault.
 * Used by dataguard_policy_explain to report coverage.
 */
export function size(): number {
  return store.size;
}

/**
 * List all placeholder strings in the vault.
 * Does NOT expose originals — safe to return to agent.
 */
export function listPlaceholders(): string[] {
  return Array.from(store.keys());
}

/**
 * Clear vault (rarely needed, mainly for testing).
 */
export function clear(): void {
  store.clear();
}
