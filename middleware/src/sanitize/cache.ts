// ============================================================================
// FILE-BASED CACHE FOR SANITIZED ARTIFACTS
// ============================================================================
// Avoids re-sanitizing the same file if mtime/size haven't changed.

import fs from "fs";
import path from "path";
import crypto from "crypto";
import type { CacheKey, CacheEntry, PdfRedactCacheEntry } from "../types";

/**
 * Root directory for cached artifacts.
 * Set by initCache().
 */
let cacheDir: string | null = null;

/**
 * Initialize cache by setting the root directory.
 * Creates directory if it doesn't exist.
 */
export function initCache(dir: string): void {
  cacheDir = dir;
  try {
    fs.mkdirSync(dir, { recursive: true });
  } catch {
    // Directory may already exist or permission denied — non-fatal
  }
}

/**
 * Generate a hash key from a CacheKey object.
 * Format: SHA-256 of "absolutePath|mtime|size"
 */
function cacheKeyHash(key: CacheKey): string {
  const raw = `${key.absolutePath}|${key.mtime}|${key.size}`;
  return crypto.createHash("sha256").update(raw).digest("hex");
}

/**
 * Resolve a cache key hash to a file path.
 * Uses two-level directory sharding to avoid filesystem performance issues:
 * cache/ab/cd/abcd...json
 */
function cacheFilePath(hash: string): string {
  if (!cacheDir) throw new Error("Cache not initialized");
  return path.join(cacheDir, hash.slice(0, 2), hash.slice(2, 4), `${hash}.json`);
}

/**
 * Retrieve a cached entry if it exists.
 * Returns null if not found or if cache is not initialized.
 */
export function get(key: CacheKey): CacheEntry | null {
  if (!cacheDir) return null;

  const file = cacheFilePath(cacheKeyHash(key));
  try {
    const raw = fs.readFileSync(file, "utf-8");
    return JSON.parse(raw) as CacheEntry;
  } catch {
    // File not found, corrupted JSON, or permission error — treat as cache miss
    return null;
  }
}

/**
 * Store a cache entry.
 * Non-fatal: silently fails if write fails.
 */
export function set(key: CacheKey, entry: CacheEntry): void {
  if (!cacheDir) return;

  const hash = cacheKeyHash(key);
  const file = cacheFilePath(hash);

  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(entry), "utf-8");
  } catch {
    // Non-fatal: permission error, disk full, etc. — continue without cache
  }
}

/**
 * Clear all cached entries (mainly useful for testing).
 */
export function clearAll(): void {
  if (!cacheDir) return;
  try {
    fs.rmSync(cacheDir, { recursive: true, force: true });
    fs.mkdirSync(cacheDir, { recursive: true });
  } catch {
    // Non-fatal
  }
}

// ---- PDF Visual Redaction Cache ----

/**
 * Generate a PDF-redact-specific cache key hash.
 * Uses a "pdf-redact:" namespace prefix to prevent collision with text cache.
 */
function pdfRedactCacheKeyHash(key: CacheKey): string {
  const raw = `pdf-redact:${key.absolutePath}|${key.mtime}|${key.size}`;
  return crypto.createHash("sha256").update(raw).digest("hex");
}

/**
 * Resolve a PDF-redact cache key hash to a file path.
 * Stored under pdf-redacted/ subdirectory.
 */
function pdfRedactCacheFilePath(hash: string): string {
  if (!cacheDir) throw new Error("Cache not initialized");
  return path.join(cacheDir, "pdf-redacted", hash.slice(0, 2), hash.slice(2, 4), `${hash}.json`);
}

/**
 * Retrieve a cached PDF redaction entry if it exists.
 * Returns null if not found or if cache is not initialized.
 */
export function getPdfRedact(key: CacheKey): PdfRedactCacheEntry | null {
  if (!cacheDir) return null;

  const file = pdfRedactCacheFilePath(pdfRedactCacheKeyHash(key));
  try {
    const raw = fs.readFileSync(file, "utf-8");
    return JSON.parse(raw) as PdfRedactCacheEntry;
  } catch {
    // File not found, corrupted JSON, or permission error — treat as cache miss
    return null;
  }
}

/**
 * Store a PDF redaction cache entry.
 * Non-fatal: silently fails if write fails.
 */
export function setPdfRedact(key: CacheKey, entry: PdfRedactCacheEntry): void {
  if (!cacheDir) return;

  const hash = pdfRedactCacheKeyHash(key);
  const file = pdfRedactCacheFilePath(hash);

  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(entry), "utf-8");
  } catch {
    // Non-fatal: permission error, disk full, etc. — continue without cache
  }
}
