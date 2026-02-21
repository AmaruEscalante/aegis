// ============================================================================
// PII & SECRET DETECTION ENGINE — Regex + Shannon Entropy
// ============================================================================

import type { Detection, PiiCategory } from "../types";

// Pattern registry — order matters for overlapping matches
// URLs first to avoid matching user:pass@domain as separate entities
const PATTERNS: Array<{ category: PiiCategory; regex: RegExp }> = [
  // High-priority structural patterns
  { category: "SSN", regex: /\b\d{3}-\d{2}-\d{4}\b/g },
  { category: "CREDIT_CARD", regex: /\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6011\d{12})\b/g },
  { category: "IBAN", regex: /\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b/g },
  { category: "PHONE", regex: /\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b/g },

  // Email — before URL to avoid domain-part confusion
  { category: "EMAIL", regex: /\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b/g },

  // Network
  { category: "IP_ADDRESS", regex: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g },
  { category: "URL", regex: /https?:\/\/[^\s"'<>]+/g },

  // Secrets by prefix
  {
    category: "SECRET",
    regex: /\b(?:sk[-_][a-zA-Z0-9]{20,}|pk_(?:live|test)_[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|AKIA[A-Z0-9]{16}|xox[bpoa]-[a-zA-Z0-9\-]+)\b/g
  },
];

const ENTROPY_MIN_BITS = 4.0;
const ENTROPY_MIN_LEN = 20;
// Token regex: contiguous non-whitespace, non-punctuation with minimum length
const TOKEN_REGEX = /[^\s"'`\n\r,;:{}[\]()]{20,}/g;

/**
 * Calculate Shannon entropy (in bits) for a string.
 * Lower entropy = more predictable (text)
 * Higher entropy = more random (encrypted/encoded secrets)
 */
function shannonEntropy(s: string): number {
  const freq = new Map<string, number>();
  for (const c of s) {
    freq.set(c, (freq.get(c) ?? 0) + 1);
  }
  let entropy = 0;
  for (const count of freq.values()) {
    const p = count / s.length;
    entropy -= p * Math.log2(p);
  }
  return entropy;
}

/**
 * Build a placeholder in the form __CATEGORY_n__ where n is a per-category counter.
 * Example: __EMAIL_1__, __EMAIL_2__, __SECRET_1__
 */
function buildPlaceholder(
  counters: Map<PiiCategory, number>,
  cat: PiiCategory
): string {
  const n = (counters.get(cat) ?? 0) + 1;
  counters.set(cat, n);
  return `__${cat}_${n}__`;
}

/**
 * Detect PII and secrets in text using regex patterns and entropy analysis.
 * Returns list of detections sorted by start offset.
 *
 * Avoids double-tagging overlapping matches using a "covered" set.
 */
export function detect(text: string): Detection[] {
  const detections: Detection[] = [];
  const counters = new Map<PiiCategory, number>();
  const covered = new Set<string>(); // "start:end" keys to prevent double-tagging

  // --- PASS 1: Regex Patterns ---
  for (const { category, regex } of PATTERNS) {
    regex.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = regex.exec(text)) !== null) {
      const key = `${m.index}:${m.index + m[0].length}`;
      if (covered.has(key)) continue;

      covered.add(key);
      detections.push({
        category,
        value: m[0],
        start: m.index,
        end: m.index + m[0].length,
        placeholder: buildPlaceholder(counters, category),
      });
    }
  }

  // --- PASS 2: Shannon Entropy (for unknown high-entropy tokens) ---
  TOKEN_REGEX.lastIndex = 0;
  let tm: RegExpExecArray | null;
  while ((tm = TOKEN_REGEX.exec(text)) !== null) {
    const key = `${tm.index}:${tm.index + tm[0].length}`;
    if (covered.has(key)) continue; // Already tagged by regex

    if (shannonEntropy(tm[0]) >= ENTROPY_MIN_BITS) {
      covered.add(key);
      detections.push({
        category: "HIGH_ENTROPY",
        value: tm[0],
        start: tm.index,
        end: tm.index + tm[0].length,
        placeholder: buildPlaceholder(counters, "HIGH_ENTROPY"),
      });
    }
  }

  // Sort ascending by start offset for deterministic application
  return detections.sort((a, b) => a.start - b.start);
}

/**
 * Apply detections to text by replacing matched regions with placeholders.
 * Processes left-to-right to avoid offset drift.
 * Assumes detections are sorted by start offset.
 */
export function applyRedactions(text: string, detections: Detection[]): string {
  let result = "";
  let cursor = 0;

  for (const d of detections) {
    // Copy text before this detection
    result += text.slice(cursor, d.start);
    // Replace with placeholder
    result += d.placeholder;
    // Move cursor past this detection
    cursor = d.end;
  }

  // Append remaining text after last detection
  result += text.slice(cursor);
  return result;
}
