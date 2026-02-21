// ============================================================================
// PDF VISUAL REDACTION PIPELINE
// ============================================================================
// Extracts text tokens with bounding boxes from a PDF, identifies PII via
// regex + LLM, then draws opaque black rectangles over those positions using
// pdf-lib. Saves the result as a new PDF file in the cache directory.
// ============================================================================

import fs from "fs";
import path from "path";
import http from "http";
import crypto from "crypto";
import type {
  DataGuardConfig,
  PdfTextToken,
  LlmRedactCoordResponse,
  RedactionRect,
  PdfRedactResult,
} from "../types";
import { detect } from "./detector";
import { buildPdfRedactPrompt, buildLlmPiiAnalysisPrompt } from "./prompts";
import { addMappings } from "./vault";
import { log } from "./audit";

// ---------------------------------------------------------------------------
// Ollama helper (mirrors sanitize.ts — kept local to avoid circular imports)
// ---------------------------------------------------------------------------

function ollamaChat(
  baseUrl: string,
  model: string,
  prompt: string,
  timeoutMs: number
): Promise<string> {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      model,
      messages: [{ role: "user", content: prompt }],
      stream: false,
    });
    const url = new URL(`${baseUrl}/api/chat`);
    const req = http.request(
      {
        hostname: url.hostname || "127.0.0.1",
        port: Number(url.port) || 11434,
        path: url.pathname || "/api/chat",
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
        },
      },
      (res) => {
        let data = "";
        res.on("data", (chunk: Buffer) => {
          data += chunk.toString("utf-8");
        });
        res.on("end", () => {
          try {
            const parsed = JSON.parse(data);
            resolve(parsed?.message?.content ?? "");
          } catch (err) {
            reject(new Error(`Failed to parse Ollama response: ${err}`));
          }
        });
      }
    );
    req.setTimeout(timeoutMs, () => {
      req.destroy();
      reject(new Error("Ollama timeout"));
    });
    req.on("error", (err) => {
      reject(new Error(`Ollama request failed: ${err.message}`));
    });
    req.write(body);
    req.end();
  });
}

// ---------------------------------------------------------------------------
// Step 1: Extract PDF tokens with bounding boxes using pdfjs-dist
// ---------------------------------------------------------------------------

export async function extractPdfTokens(
  filePath: string
): Promise<PdfTextToken[]> {
  // Dynamic import: pdfjs-dist is an optional dependency
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pdfjs = await import("pdfjs-dist/legacy/build/pdf.js" as any);

  const data = new Uint8Array(fs.readFileSync(filePath));
  const loadingTask = pdfjs.getDocument({ data, verbosity: 0 });
  const pdfDoc = await loadingTask.promise;

  const tokens: PdfTextToken[] = [];
  let globalId = 0;

  for (let pageIndex = 0; pageIndex < pdfDoc.numPages; pageIndex++) {
    const page = await pdfDoc.getPage(pageIndex + 1); // pdf.js pages are 1-based
    const viewport = page.getViewport({ scale: 1.0 });
    const content = await page.getTextContent();

    for (const item of content.items) {
      // TextItem has: str, transform [a,b,c,d,e,f], width, height
      // transform[4] = x (points from left), transform[5] = y (points from bottom)
      const ti = item as {
        str: string;
        transform: number[];
        width: number;
        height: number;
      };

      if (!ti.str || ti.str.trim() === "") continue;

      // Split by whitespace to get individual word tokens
      // Each word inherits the run's y/height; x is estimated by character proportion
      const words = ti.str.split(/\s+/).filter((w) => w.length > 0);
      const runX = ti.transform[4];
      const runY = viewport.height - ti.transform[5] - (ti.height || 12);
      // Distribute x proportionally within the run width
      const charWidth =
        words.length > 0 ? ti.width / ti.str.length : 8;

      let cursorX = runX;
      for (const word of words) {
        const wordWidth = charWidth * word.length;
        tokens.push({
          id: globalId++,
          pageIndex,
          text: word,
          x: cursorX,
          y: runY,
          width: wordWidth,
          height: ti.height || 12,
        });
        cursorX += wordWidth + charWidth; // add one char space between words
      }
    }
  }

  return tokens;
}

// ---------------------------------------------------------------------------
// Step 2: Regex pre-filter — returns IDs of tokens matching PII patterns
// ---------------------------------------------------------------------------

function regexFilterTokenIds(tokens: PdfTextToken[]): Set<number> {
  const flagged = new Set<number>();

  for (const token of tokens) {
    const detections = detect(token.text);
    if (detections.length > 0) {
      flagged.add(token.id);
      // Store regex detections in vault immediately (preserves security model)
      addMappings(
        detections.map((d) => ({
          placeholder: d.placeholder,
          original: d.value,
          category: d.category,
        }))
      );
    }
  }

  return flagged;
}

// ---------------------------------------------------------------------------
// Step 3: LLM pass — returns IDs the LLM selected for redaction
// ---------------------------------------------------------------------------

async function llmSelectTokenIds(
  tokens: PdfTextToken[],
  config: DataGuardConfig
): Promise<Set<number>> {
  const prompt = buildPdfRedactPrompt(tokens);
  const raw = await ollamaChat(
    config.ollamaBaseUrl,
    config.ollamaModel,
    prompt,
    config.ollamaTimeoutMs
  );

  // Strip markdown code fences (Gemma sometimes wraps output)
  const stripped = raw
    .replace(/^```(?:json)?\s*/m, "")
    .replace(/```\s*$/m, "")
    .trim();

  let parsed: LlmRedactCoordResponse;
  try {
    parsed = JSON.parse(stripped);
  } catch {
    throw new Error(
      `LLM returned invalid JSON for coordinate redaction: ${stripped.slice(0, 200)}`
    );
  }

  if (!parsed.redact || !Array.isArray(parsed.redact)) {
    throw new Error("LLM response missing 'redact' array");
  }

  return new Set(parsed.redact.map((r) => r.id));
}

// ---------------------------------------------------------------------------
// Step 4: Build RedactionRect list from selected token IDs
//         Adjacent tokens on the same line are merged into a single rectangle
//         to reduce the number of draw calls and produce cleaner output.
// ---------------------------------------------------------------------------

function buildRedactionRects(
  tokens: PdfTextToken[],
  selectedIds: Set<number>
): RedactionRect[] {
  const selected = tokens.filter((t) => selectedIds.has(t.id));
  if (selected.length === 0) return [];

  // Group by pageIndex + approximate y coordinate (within 2pt = same line)
  type LineKey = string; // "pageIndex|roundedY"
  const lineGroups = new Map<LineKey, PdfTextToken[]>();

  for (const token of selected) {
    const roundedY = Math.round(token.y / 2) * 2; // snap to 2pt grid
    const key: LineKey = `${token.pageIndex}|${roundedY}`;
    if (!lineGroups.has(key)) lineGroups.set(key, []);
    lineGroups.get(key)!.push(token);
  }

  const rects: RedactionRect[] = [];
  const GAP_THRESHOLD = 10; // merge tokens within 10pt on same line

  for (const [key, group] of lineGroups) {
    const [pageStr] = key.split("|");
    const pageIndex = parseInt(pageStr, 10);

    // Sort by x to enable left-to-right merging
    group.sort((a, b) => a.x - b.x);

    // Merge into runs
    let runStart = group[0];
    let runEnd = group[0];

    for (let i = 1; i < group.length; i++) {
      const curr = group[i];
      const gap = curr.x - (runEnd.x + runEnd.width);
      if (gap <= GAP_THRESHOLD) {
        runEnd = curr;
      } else {
        // Flush current run
        rects.push({
          pageIndex,
          x: runStart.x - 1, // 1pt padding
          y: runStart.y - 1,
          width: runEnd.x + runEnd.width - runStart.x + 2,
          height: Math.max(runStart.height, runEnd.height) + 2,
          reason: "PII redacted",
        });
        runStart = curr;
        runEnd = curr;
      }
    }

    // Flush last run
    rects.push({
      pageIndex,
      x: runStart.x - 1,
      y: runStart.y - 1,
      width: runEnd.x + runEnd.width - runStart.x + 2,
      height: Math.max(runStart.height, runEnd.height) + 2,
      reason: "PII redacted",
    });
  }

  return rects;
}

// ---------------------------------------------------------------------------
// Step 5: Apply redaction rectangles to PDF using pdf-lib
// ---------------------------------------------------------------------------

async function applyRectsToPdf(
  sourcePath: string,
  rects: RedactionRect[],
  outputPath: string
): Promise<void> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { PDFDocument, rgb } = await import("pdf-lib" as any);

  const sourceBytes = fs.readFileSync(sourcePath);
  const pdfDoc = await PDFDocument.load(sourceBytes);
  const pages = pdfDoc.getPages();

  for (const rect of rects) {
    const page = pages[rect.pageIndex];
    if (!page) continue;

    const { height: pageHeight } = page.getSize();

    // pdf-lib coordinate origin is bottom-left, y increases upward.
    // Our y is already measured from top (pdfjs-dist flipped it in extractPdfTokens).
    // We need to convert: pdf-lib y = pageHeight - our_y - rectHeight
    const pdfLibY = pageHeight - rect.y - rect.height;

    page.drawRectangle({
      x: rect.x,
      y: pdfLibY,
      width: rect.width,
      height: rect.height,
      color: rgb(0, 0, 0),
      opacity: 1,
    });
  }

  const redactedBytes = await pdfDoc.save();
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, redactedBytes);
}

// ---------------------------------------------------------------------------
// Step 6: Resolve deterministic output path in cache directory
// ---------------------------------------------------------------------------

function resolveOutputPath(sourcePath: string, cacheDir: string): string {
  const hash = crypto
    .createHash("sha256")
    .update(`pdf-visual:${sourcePath}`)
    .digest("hex");
  return path.join(cacheDir, "pdf-redacted", hash.slice(0, 2), `${hash}.pdf`);
}

// ---------------------------------------------------------------------------
// ENHANCED: LLM-driven comprehensive analysis
// ---------------------------------------------------------------------------

/**
 * LLM-based analysis response: comprehensive PII detection with context
 */
interface LlmPiiAnalysis {
  sensitive_items: Array<{
    type: string;        // CATEGORY
    value: string;       // actual sensitive text
    context: string;     // surrounding snippet
    reason: string;      // why it's sensitive
  }>;
  summary: string;
}

/**
 * Enhanced PDF redaction: LLM comprehensively analyzes full content,
 * then we find ALL occurrences in the PDF and redact them.
 */
export async function redactPdfWithLlmAnalysis(
  sourcePath: string,
  extractedText: string,
  config: DataGuardConfig
): Promise<PdfRedactResult> {
  // Step 1: Extract tokens (we need coordinates)
  const tokens = await extractPdfTokens(sourcePath);

  // Step 2: Send FULL document text to LLM for comprehensive analysis
  let llmAnalysis: LlmPiiAnalysis | null = null;
  let method: PdfRedactResult["method"] = "regex-only";

  try {
    const prompt = buildLlmPiiAnalysisPrompt(extractedText);
    const raw = await ollamaChat(
      config.ollamaBaseUrl,
      config.ollamaModel,
      prompt,
      config.ollamaTimeoutMs
    );

    const stripped = raw
      .replace(/^```(?:json)?\s*/m, "")
      .replace(/```\s*$/m, "")
      .trim();

    llmAnalysis = JSON.parse(stripped) as LlmPiiAnalysis;
    method = "llm+regex";

    // Store all LLM-found items in vault
    if (llmAnalysis && llmAnalysis.sensitive_items) {
      addMappings(
        llmAnalysis.sensitive_items.map((item, idx) => ({
          placeholder: `__${item.type}_${idx + 1}__`,
          original: item.value,
          category: item.type as any,
        }))
      );
    }
  } catch (err) {
    log({
      timestamp: new Date().toISOString(),
      event: "pdf_redactor_llm_analysis",
      action: "sanitize",
      reason: `LLM comprehensive analysis failed, falling back to regex: ${err}`,
    });
  }

  // Step 3: Build set of text to find (LLM findings + regex detections)
  const toRedact = new Set<string>();

  if (llmAnalysis?.sensitive_items) {
    for (const item of llmAnalysis.sensitive_items) {
      toRedact.add(item.value);
    }
  }

  // Also run regex as fallback for items LLM might miss
  for (const token of tokens) {
    const detections = detect(token.text);
    for (const det of detections) {
      toRedact.add(det.value);
    }
  }

  // Step 4: Find ALL tokens that match the sensitive text
  const redactTokenIds = new Set<number>();
  for (const token of tokens) {
    if (toRedact.has(token.text)) {
      redactTokenIds.add(token.id);
    }
  }

  // Step 5: Build rectangles from matched tokens
  const rects = buildRedactionRects(tokens, redactTokenIds);

  // Step 6: Apply rectangles to PDF and save
  const outputPath = resolveOutputPath(sourcePath, config.cacheDir);
  await applyRectsToPdf(sourcePath, rects, outputPath);

  // Step 7: Audit
  log({
    timestamp: new Date().toISOString(),
    event: "pdf_redactor_llm",
    path: sourcePath,
    action: "sanitize",
    redactionCount: rects.length,
    method,
    reason: `LLM analysis found ${llmAnalysis?.sensitive_items?.length || 0} items`,
  });

  return {
    redactedPdfPath: outputPath,
    tokenCount: tokens.length,
    redactionCount: rects.length,
    method,
  };
}

// ---------------------------------------------------------------------------
// Main export: full PDF visual redaction pipeline
// ---------------------------------------------------------------------------

export async function redactPdfVisually(
  sourcePath: string,
  config: DataGuardConfig
): Promise<PdfRedactResult> {
  // Step 1: Extract tokens
  const tokens = await extractPdfTokens(sourcePath);

  // Step 2: Regex pre-filter (fast, deterministic, vault-safe)
  const regexFlagged = regexFilterTokenIds(tokens);

  // Step 3: LLM pass (optional, fallback to regex-only)
  let llmFlagged = new Set<number>();
  let method: PdfRedactResult["method"] = "regex-only";

  try {
    llmFlagged = await llmSelectTokenIds(tokens, config);
    method = "llm+regex";
  } catch (err) {
    // LLM unavailable or returned bad JSON — proceed with regex-only
    log({
      timestamp: new Date().toISOString(),
      event: "pdf_redactor",
      action: "sanitize",
      reason: `LLM pass failed, using regex-only: ${err}`,
    });
  }

  // Union of regex and LLM selections
  const allFlagged = new Set([...regexFlagged, ...llmFlagged]);

  // Step 4: Build rectangles (merge adjacent tokens)
  const rects = buildRedactionRects(tokens, allFlagged);

  // Step 5: Apply rectangles to PDF and save
  const outputPath = resolveOutputPath(sourcePath, config.cacheDir);
  await applyRectsToPdf(sourcePath, rects, outputPath);

  // Step 6: Audit
  log({
    timestamp: new Date().toISOString(),
    event: "pdf_redactor",
    path: sourcePath,
    action: "sanitize",
    redactionCount: rects.length,
    method,
  });

  return {
    redactedPdfPath: outputPath,
    tokenCount: tokens.length,
    redactionCount: rects.length,
    method,
  };
}
