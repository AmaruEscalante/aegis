// ============================================================================
// CORE TYPES & INTERFACES FOR AEGIS PLUGIN
// ============================================================================

// ---- Configuration ----
export type LlmProvider = "ollama" | "openrouter";

export interface DataGuardConfig {
  denyPathGlobs: string[];
  allowedRoots: string[];
  sanitizeAlwaysGlobs: string[];
  maxFileBytes: number;
  cacheDir: string;
  auditLogPath: string;

  // LLM Provider Selection
  llmProvider: LlmProvider;  // Default: "ollama", switch to "openrouter" for cloud

  // LLM Redaction Mode
  llmMode: "prompt" | "tool-calling";  // Default: "tool-calling" for surgical edits via tool calls

  // Ollama Configuration (local LLM)
  ollamaBaseUrl: string;
  ollamaModel: string;
  ollamaTimeoutMs: number;

  // OpenRouter Configuration (cloud LLM)
  openrouterApiKey: string;
  openrouterModel: string;
  openrouterTimeoutMs: number;

  // Aegis Router (FunctionGemma classification bridge)
  aegisEnabled: boolean;           // true = classify first, false = sanitize-everything legacy mode
  aegisBridgeUrl: string;          // default: "http://127.0.0.1:7523"
  aegisBridgeTimeoutMs: number;    // default: 10_000
}

// ---- Policy Verdicts ----
export type PathVerdict = "deny" | "sanitize" | "passthrough";

export interface PathCheckResult {
  verdict: PathVerdict;
  reason: string;
}

// ---- File Extraction ----
export type FileFormat = "text" | "pdf" | "docx" | "binary";

export interface ExtractResult {
  text: string;
  format: FileFormat;
  sizeBytes: number;
}

// ---- PII Detection ----
export type PiiCategory =
  | "EMAIL"
  | "PHONE"
  | "SSN"
  | "CREDIT_CARD"
  | "IBAN"
  | "URL"
  | "IP_ADDRESS"
  | "SECRET"
  | "HIGH_ENTROPY";

export interface Detection {
  category: PiiCategory;
  value: string;
  start: number;  // char offset in source text
  end: number;
  placeholder: string;  // format: __CATEGORY_n__
}

// ---- Sanitization ----
export interface LlmRedaction {
  type: string;
  placeholder: string;
  context: string;  // surrounding text snippet
}

export interface LlmSanitizeResponse {
  sanitized_text: string;
  redactions: LlmRedaction[];
  summary: string;
}

export interface SanitizeResult {
  sanitized_text: string;
  redactions: Detection[];
  llm_summary?: string;
  method: "llm+regex" | "regex-only";
}

// ---- Caching ----
export interface CacheKey {
  absolutePath: string;
  mtime: number;  // fs.statSync().mtimeMs
  size: number;   // bytes
}

export interface CacheEntry {
  sanitizedText: string;
  redactions: Detection[];
  method: SanitizeResult["method"];
  cachedAt: number;  // Date.now()
}

// ---- Vault (In-memory Placeholder Store) ----
export interface VaultEntry {
  placeholder: string;
  original: string;
  category: PiiCategory;
  addedAt: number;
}

// ---- Audit Logging ----
export type AuditAction =
  | "block"
  | "sanitize"
  | "cache_hit"
  | "deny_path"
  | "egress_blocked"
  | "read"
  | "search"
  | "patch"
  | "classify_safe"
  | "block_transfer"
  | "escalate";

export interface AuditEvent {
  timestamp: string;  // ISO8601
  event: string;  // tool name or hook name
  toolName?: string;
  path?: string;
  action: AuditAction;
  reason?: string;
  redactionCount?: number;
  method?: string;
}

// ---- OpenClaw Plugin API ----
export interface BeforeToolCallContext {
  toolName: string;
  params: Record<string, unknown>;
}

export interface BeforeToolCallResult {
  params?: Record<string, unknown>;
  block?: boolean;
  blockReason?: string;
}

export interface OpenClawPluginApi {
  on?(hookName: string, handler: (...args: unknown[]) => unknown): void;
  registerTool?(spec: {
    name: string;
    description: string;
    parameters: Record<string, unknown>;
    execute: (...args: unknown[]) => Promise<unknown>;
  }): void;
}

// ---- PDF Visual Redaction ----

/** A single word/token extracted from a PDF page with its bounding box. */
export interface PdfTextToken {
  id: number;           // Sequential integer, unique within the document
  pageIndex: number;    // 0-based page number
  text: string;         // The word or run text
  x: number;            // Left edge in PDF user units (points)
  y: number;            // Bottom edge in PDF user units (points, origin at bottom-left)
  width: number;
  height: number;
}

/** LLM response for coordinate-based redaction decisions. */
export interface LlmRedactCoordResponse {
  redact: Array<{
    id: number;         // Token ID to redact
    reason: string;     // Why this token should be redacted (EMAIL, SSN, etc.)
  }>;
  summary: string;
}

/** A resolved redaction rectangle, ready for pdf-lib to draw. */
export interface RedactionRect {
  pageIndex: number;
  x: number;
  y: number;
  width: number;
  height: number;
  reason: string;       // Stored in vault audit, never returned to agent
}

/** Result from the full PDF visual redaction pipeline. */
export interface PdfRedactResult {
  redactedPdfPath: string;    // Absolute path to the saved redacted PDF
  tokenCount: number;         // Total tokens extracted
  redactionCount: number;     // Number of rectangles drawn
  method: "llm+regex" | "regex-only";
}

/** Cache entry for a redacted PDF artifact. */
export interface PdfRedactCacheEntry {
  redactedPdfPath: string;
  redactionCount: number;
  method: PdfRedactResult["method"];
  cachedAt: number;
}

// ---- Aegis Router (FunctionGemma Classification) ----

/** Verdict returned by the Aegis FunctionGemma classification bridge. */
export type AegisVerdict = "safe" | "flag_pii" | "block" | "escalate";

/** Result from the Aegis classification bridge. */
export interface ClassifyResult {
  verdict: AegisVerdict;
  reason: string;
  confidence: number;
  pii_types?: string;          // Comma-separated PII types (only for flag_pii)
  time_ms: number;
}

/** Health-check response from the Aegis bridge server. */
export interface BridgeHealth {
  status: "ok" | "unreachable";
  backend?: "cactus" | "transformers";
  model?: string;
}

/** Read result when Aegis classification short-circuits the pipeline. */
export interface AegisReadResult {
  content: string | null;
  format: string;
  aegis_verdict: AegisVerdict;
  aegis_reason: string;
  aegis_confidence: number;
  redaction_count: number;
  method: string;
  cached: boolean;
  escalation?: {
    reason: string;
    confidence: number;
    message: string;
  };
}
