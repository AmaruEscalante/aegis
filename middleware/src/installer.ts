/**
 * Hook installer — adds the Aegis PreToolUse hook to ~/.claude/settings.json
 * additively (preserves existing hooks), with timestamped backup before
 * any mutation.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';

export const HOOK_NAME = 'aegis-gate:enforce-read-routing';
export const HOOK_MATCHER = 'Read|Glob|Grep';

interface InstallOptions {
    settingsPath: string;
    hookScript: string;
}

interface UninstallOptions {
    settingsPath: string;
}

/**
 * Find the Aegis hook entry in the settings object, or null if absent.
 */
export function findAegisHookEntry(settings: any): any | null {
    const entries = settings?.hooks?.PreToolUse;
    if (!Array.isArray(entries)) return null;
    return entries.find((e: any) => e?.name === HOOK_NAME) ?? null;
}

/**
 * Install the Aegis hook. Idempotent. Creates settings.json if absent.
 * Returns the backup path (or null if no backup was needed).
 */
export async function installHook(opts: InstallOptions): Promise<string | null> {
    let settings: any = {};
    let backupPath: string | null = null;

    if (fs.existsSync(opts.settingsPath)) {
        const raw = fs.readFileSync(opts.settingsPath, 'utf8');
        try {
            settings = JSON.parse(raw);
        } catch (e: any) {
            throw new Error(
                `Refusing to install: ${opts.settingsPath} is not valid JSON. ` +
                `Fix the file manually before running 'npx aegis-gate' again. (${e.message})`
            );
        }

        // Backup before mutating
        const ts = new Date().toISOString().replace(/[:.]/g, '-');
        const backupDir = path.join(path.dirname(opts.settingsPath), '..', '.aegis-gate', 'backups');
        fs.mkdirSync(backupDir, { recursive: true });
        backupPath = path.join(backupDir, `settings.json.${ts}`);
        fs.copyFileSync(opts.settingsPath, backupPath);
    } else {
        // Ensure parent dir exists for new settings.json
        fs.mkdirSync(path.dirname(opts.settingsPath), { recursive: true });
    }

    // Idempotency check
    if (findAegisHookEntry(settings)) {
        return backupPath;  // already installed
    }

    // Additive patch
    if (!settings.hooks) settings.hooks = {};
    if (!Array.isArray(settings.hooks.PreToolUse)) settings.hooks.PreToolUse = [];
    settings.hooks.PreToolUse.push({
        name: HOOK_NAME,
        matcher: HOOK_MATCHER,
        hooks: [{ type: 'command', command: `node ${opts.hookScript}` }],
    });

    fs.writeFileSync(opts.settingsPath, JSON.stringify(settings, null, 2) + '\n');
    return backupPath;
}

/**
 * Remove the Aegis hook entry. Leaves other entries untouched.
 * No-op if settings.json doesn't exist or doesn't contain the entry.
 */
export async function uninstallHook(opts: UninstallOptions): Promise<void> {
    if (!fs.existsSync(opts.settingsPath)) return;
    const raw = fs.readFileSync(opts.settingsPath, 'utf8');
    let settings: any;
    try {
        settings = JSON.parse(raw);
    } catch {
        return;  // can't parse; nothing to remove
    }

    const entries = settings?.hooks?.PreToolUse;
    if (!Array.isArray(entries)) return;

    const filtered = entries.filter((e: any) => e?.name !== HOOK_NAME);
    if (filtered.length === entries.length) return;  // nothing changed

    settings.hooks.PreToolUse = filtered;
    fs.writeFileSync(opts.settingsPath, JSON.stringify(settings, null, 2) + '\n');
}
