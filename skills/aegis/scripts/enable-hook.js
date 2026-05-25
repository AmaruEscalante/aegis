#!/usr/bin/env node
const path = require('node:path');
const os = require('node:os');
// Delegate to the npm-installed CLI's installer
const { installHook } = require(path.join(os.homedir(), '.aegis-gate', 'middleware', 'dist', 'installer.js'));

const SETTINGS_PATH = path.join(os.homedir(), '.claude', 'settings.json');
const HOOK_SCRIPT = path.join(os.homedir(), '.aegis-gate', 'middleware', 'scripts', 'hook-enforce.js');

installHook({ settingsPath: SETTINGS_PATH, hookScript: HOOK_SCRIPT })
    .then(backup => {
        console.log(`✓ Hook enabled${backup ? ` (backup: ${backup})` : ''}`);
    })
    .catch(e => { console.error(`Error: ${e.message}`); process.exit(1); });
