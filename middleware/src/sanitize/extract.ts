// ============================================================================
// TEXT EXTRACTION — PDF, DOCX, Plain Text
// ============================================================================

import fs from "fs";
import path from "path";
import { execSync } from "child_process";
import type { ExtractResult, FileFormat } from "../types";

const PDF_EXTENSIONS = new Set([".pdf"]);
const DOCX_EXTENSIONS = new Set([".docx", ".doc"]);

/**
 * Detect file format from extension.
 */
function detectFormat(filePath: string): FileFormat {
  const ext = path.extname(filePath).toLowerCase();

  if (PDF_EXTENSIONS.has(ext)) return "pdf";
  if (DOCX_EXTENSIONS.has(ext)) return "docx";
  return "text"; // Default: treat as UTF-8 text
}

/**
 * Extract text from PDF using pdftotext (preferred) or pdf-parse (fallback).
 */
async function extractPdf(filePath: string): Promise<string> {
  // Try pdftotext first (poppler-utils) — more reliable, no native bindings
  try {
    const result = execSync(`pdftotext -layout "${filePath}" -`, {
      maxBuffer: 10 * 1024 * 1024,
      timeout: 30_000,
    });
    return result.toString("utf-8");
  } catch {
    // Fallback to pdf-parse npm package
    try {
      const pdfParse = await import("pdf-parse");
      const buffer = fs.readFileSync(filePath);
      const data = await pdfParse.default(buffer);
      return data.text || "";
    } catch (err) {
      throw new Error(
        `Could not extract PDF: pdftotext not found and pdf-parse failed: ${err}`
      );
    }
  }
}

/**
 * Extract text from DOCX using mammoth.
 */
async function extractDocx(filePath: string): Promise<string> {
  try {
    const mammoth = await import("mammoth");
    const result = await mammoth.extractRawText({ path: filePath });
    return result.value || "";
  } catch (err) {
    throw new Error(`Failed to extract DOCX: ${err}`);
  }
}

/**
 * Extract text from a file.
 * Handles PDF, DOCX, and plain text formats.
 * Enforces maxFileBytes limit.
 */
export async function extractText(
  filePath: string,
  maxBytes: number
): Promise<ExtractResult> {
  const stat = fs.statSync(filePath);

  if (stat.size > maxBytes) {
    throw new Error(
      `File exceeds maxFileBytes (${stat.size} > ${maxBytes})`
    );
  }

  const format = detectFormat(filePath);
  let text: string;

  try {
    switch (format) {
      case "pdf":
        text = await extractPdf(filePath);
        break;

      case "docx":
        text = await extractDocx(filePath);
        break;

      default:
        // Plain text: read as UTF-8
        text = fs.readFileSync(filePath, "utf-8");
    }
  } catch (err) {
    throw new Error(`Failed to extract text from ${format}: ${err}`);
  }

  return {
    text,
    format,
    sizeBytes: stat.size,
  };
}
