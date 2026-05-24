import { describe, it, expect } from 'vitest';
import { extractText } from '../src/extract';
import * as path from 'node:path';
import * as fs from 'node:fs';

const FIXTURES = path.join(__dirname, 'fixtures');

describe('extractText', () => {
    it('returns plain text from .txt files unchanged', async () => {
        const p = path.join(FIXTURES, 'safe.txt');
        fs.writeFileSync(p, 'hello world');
        const out = await extractText(p);
        expect(out.text).toBe('hello world');
        expect(out.escalate).toBe(false);
        fs.unlinkSync(p);
    });

    it('extracts text from .pdf via pdfjs-dist', async () => {
        const p = path.join(FIXTURES, 'safe.pdf');
        const out = await extractText(p);
        expect(out.text.length).toBeGreaterThan(0);
        expect(out.escalate).toBe(false);
    });

    it('returns escalate=true for image files (.png, .jpg, .gif, .webp, .heic)', async () => {
        for (const ext of ['.png', '.jpg', '.gif', '.webp', '.heic']) {
            const p = path.join(FIXTURES, `screenshot${ext}`);
            // Create a stub file if it doesn't exist (we don't need real image content)
            if (!fs.existsSync(p)) fs.writeFileSync(p, Buffer.from([0x89, 0x50, 0x4e, 0x47]));
            const out = await extractText(p);
            expect(out.escalate).toBe(true);
            expect(out.escalateReason).toMatch(/image/i);
        }
    });

    it('returns escalate=true for files over 5MB', async () => {
        const p = path.join(FIXTURES, 'huge.txt');
        fs.writeFileSync(p, 'x'.repeat(6 * 1024 * 1024));  // 6MB
        const out = await extractText(p);
        expect(out.escalate).toBe(true);
        expect(out.escalateReason).toMatch(/size/i);
        fs.unlinkSync(p);
    });
});
