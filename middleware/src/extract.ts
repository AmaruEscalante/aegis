/**
 * File text extraction for aegis_read.
 *
 * Returns either extracted text (route to classifier) or escalate=true
 * with a reason (route directly to request_permission verdict).
 *
 * Owns the file-size policy: oversize files short-circuit to escalate
 * rather than throwing, so callers get a clean request_permission verdict
 * instead of a thrown error.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import type { FileFormat } from './types';

const DEFAULT_MAX_BYTES = 5 * 1024 * 1024;  // 5MB
const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.bmp', '.tiff']);

export interface ExtractResult {
    text: string;
    format: FileFormat;
    escalate: boolean;
    escalateReason?: string;
}

export async function extractText(
    filePath: string,
    maxBytes: number = DEFAULT_MAX_BYTES,
): Promise<ExtractResult> {
    const ext = path.extname(filePath).toLowerCase();

    // Size check first — applies to all formats. Oversize escalates (does
    // NOT throw) so the caller can return a request_permission verdict.
    const stat = fs.statSync(filePath);
    if (stat.size > maxBytes) {
        return {
            text: '',
            format: ext === '.pdf' ? 'pdf' : ext === '.docx' ? 'docx' : IMAGE_EXTS.has(ext) ? 'binary' : 'text',
            escalate: true,
            escalateReason: `File size ${stat.size} exceeds ${maxBytes}-byte limit; routing to request_permission for explicit human review.`,
        };
    }

    // Image files → escalate without attempting extraction
    if (IMAGE_EXTS.has(ext)) {
        return {
            text: '',
            format: 'binary',
            escalate: true,
            escalateReason: `Image file (${ext}); OCR not supported in v1. Routing to request_permission for human review.`,
        };
    }

    // PDF via pdfjs-dist (handles modern PDFs from pdfkit, Office, etc.)
    if (ext === '.pdf') {
        try {
            const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
            const buf = fs.readFileSync(filePath);
            const doc = await pdfjs.getDocument({
                data: new Uint8Array(buf),
                isEvalSupported: false,
                useSystemFonts: true,
            }).promise;
            let text = '';
            for (let i = 1; i <= doc.numPages; i++) {
                const page = await doc.getPage(i);
                const content = await page.getTextContent();
                text += content.items.map((it: any) => it.str).join(' ');
                if (i < doc.numPages) text += '\n';
            }
            return { text, format: 'pdf', escalate: false };
        } catch (e: any) {
            // Encrypted PDFs throw a specific error
            if (e.message?.match(/encrypt|password/i)) {
                return {
                    text: '',
                    format: 'pdf',
                    escalate: true,
                    escalateReason: 'PDF is encrypted; password input not supported in v1.',
                };
            }
            throw e;
        }
    }

    // DOCX via mammoth
    if (ext === '.docx') {
        const mammoth = require('mammoth');
        const out = await mammoth.extractRawText({ path: filePath });
        return { text: out.value, format: 'docx', escalate: false };
    }

    // Default: UTF-8 read
    return { text: fs.readFileSync(filePath, 'utf8'), format: 'text', escalate: false };
}
