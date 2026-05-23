import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
    installHook,
    uninstallHook,
    findAegisHookEntry,
    HOOK_NAME,
} from '../src/installer';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';

describe('installer', () => {
    let tmpDir: string;
    let settingsPath: string;

    beforeEach(() => {
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'aegis-installer-test-'));
        settingsPath = path.join(tmpDir, 'settings.json');
    });

    afterEach(() => {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('creates settings.json with the hook if file is absent', async () => {
        const backupPath = await installHook({ settingsPath, hookScript: '/path/to/hook.js' });
        expect(backupPath).toBeNull();  // no backup needed when file absent
        const written = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
        expect(written.hooks?.PreToolUse).toBeInstanceOf(Array);
        const aegisEntry = written.hooks.PreToolUse.find((h: any) => h.name === HOOK_NAME);
        expect(aegisEntry).toBeTruthy();
        expect(aegisEntry.matcher).toBe('Read|Glob|Grep');
    });

    it('additively patches existing settings.json without touching other keys', async () => {
        const existing = {
            theme: 'dark',
            hooks: {
                PreToolUse: [
                    { name: 'other-plugin:foo', matcher: 'Bash', hooks: [{ type: 'command', command: 'echo' }] },
                ],
            },
        };
        fs.writeFileSync(settingsPath, JSON.stringify(existing, null, 2));

        const backupPath = await installHook({ settingsPath, hookScript: '/path/to/hook.js' });
        expect(backupPath).toBeTruthy();
        expect(fs.existsSync(backupPath!)).toBe(true);

        const written = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
        expect(written.theme).toBe('dark');  // preserved
        expect(written.hooks.PreToolUse).toHaveLength(2);
        const otherEntry = written.hooks.PreToolUse.find((h: any) => h.name === 'other-plugin:foo');
        expect(otherEntry).toBeTruthy();
    });

    it('is idempotent — second install does not add a duplicate entry', async () => {
        await installHook({ settingsPath, hookScript: '/path/to/hook.js' });
        await installHook({ settingsPath, hookScript: '/path/to/hook.js' });
        const written = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
        const matches = written.hooks.PreToolUse.filter((h: any) => h.name === HOOK_NAME);
        expect(matches).toHaveLength(1);
    });

    it('uninstall removes only the aegis hook entry', async () => {
        const existing = {
            hooks: {
                PreToolUse: [
                    { name: 'other-plugin:foo', matcher: 'Bash', hooks: [{ type: 'command', command: 'echo' }] },
                ],
            },
        };
        fs.writeFileSync(settingsPath, JSON.stringify(existing, null, 2));
        await installHook({ settingsPath, hookScript: '/path/to/hook.js' });

        await uninstallHook({ settingsPath });

        const written = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
        expect(written.hooks.PreToolUse).toHaveLength(1);
        expect(written.hooks.PreToolUse[0].name).toBe('other-plugin:foo');
    });

    it('findAegisHookEntry returns the entry if present, null otherwise', () => {
        const settings1 = { hooks: { PreToolUse: [{ name: HOOK_NAME, matcher: 'Read', hooks: [] }] } };
        expect(findAegisHookEntry(settings1)).toBeTruthy();
        const settings2 = { hooks: { PreToolUse: [{ name: 'other', matcher: 'Read', hooks: [] }] } };
        expect(findAegisHookEntry(settings2)).toBeNull();
        expect(findAegisHookEntry({})).toBeNull();
    });
});
