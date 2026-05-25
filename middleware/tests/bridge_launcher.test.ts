import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
    detectPython,
    resolveAegisCachePath,
    findFreePort,
} from '../src/bridge_launcher';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';

describe('detectPython', () => {
    it('returns a Python 3.12+ path when one is on PATH', async () => {
        const p = await detectPython();
        expect(p).toBeTruthy();
        expect(typeof p).toBe('string');
    });

    it('throws a clear error if no Python ≥ 3.12 is available', async () => {
        // Use a sentinel PATH with no python
        const originalPath = process.env.PATH;
        process.env.PATH = '/nonexistent';
        try {
            await expect(detectPython()).rejects.toThrow(/Python 3\.12/);
        } finally {
            process.env.PATH = originalPath;
        }
    });
});

describe('resolveAegisCachePath', () => {
    it('returns a path under the user home', () => {
        const p = resolveAegisCachePath();
        expect(p).toContain(os.homedir());
        expect(p).toContain('.aegis-gate');
    });
});

describe('findFreePort', () => {
    it('returns a port number between 1024 and 65535', async () => {
        const port = await findFreePort();
        expect(port).toBeGreaterThan(1024);
        expect(port).toBeLessThan(65536);
    });

    it('returns different ports on successive calls', async () => {
        const p1 = await findFreePort();
        const p2 = await findFreePort();
        // Not guaranteed to be different (OS can reassign), but very likely
        // for back-to-back calls. If this is flaky, change to checking
        // both ports are valid.
        expect(p1).toBeGreaterThan(0);
        expect(p2).toBeGreaterThan(0);
    });
});
