#!/usr/bin/env node
/**
 * /aegis-status implementation.
 * Reports: hook installed? bridge reachable? recent verdict counts (from log).
 */
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

const HOOK_NAME = 'aegis-mcp:enforce-read-routing';
const SETTINGS_PATH = path.join(os.homedir(), '.claude', 'settings.json');

async function main() {
    // Check hook
    let hookInstalled = false;
    try {
        const settings = JSON.parse(fs.readFileSync(SETTINGS_PATH, 'utf8'));
        hookInstalled = (settings?.hooks?.PreToolUse ?? []).some(e => e?.name === HOOK_NAME);
    } catch { /* file absent or malformed */ }

    // Check bridge — read the latest known port from the install marker
    const portFile = path.join(os.homedir(), '.aegis-mcp', 'bridge.port');
    let bridgeStatus = 'unknown';
    let bridgeMeta = {};
    if (fs.existsSync(portFile)) {
        const port = Number(fs.readFileSync(portFile, 'utf8').trim());
        try {
            const res = await fetch(`http://127.0.0.1:${port}/health`);
            if (res.ok) {
                bridgeMeta = await res.json();
                bridgeStatus = 'ok';
            } else {
                bridgeStatus = `error (status ${res.status})`;
            }
        } catch (e) {
            bridgeStatus = `unreachable (${e.message})`;
        }
    }

    console.log('Aegis status');
    console.log('============');
    console.log(`Hook (enforce Read/Glob/Grep):  ${hookInstalled ? 'installed' : 'NOT installed'}`);
    console.log(`Bridge:                          ${bridgeStatus}`);
    if (bridgeStatus === 'ok') {
        console.log(`  embed model:    ${bridgeMeta.embed_model}`);
        console.log(`  prompt:         ${bridgeMeta.embed_task_prompt}`);
        console.log(`  device:         ${bridgeMeta.device ?? 'unknown'}`);
    }
}

main().catch(e => { console.error(`Error: ${e.message}`); process.exit(1); });
