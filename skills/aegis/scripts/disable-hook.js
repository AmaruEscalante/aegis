#!/usr/bin/env node
const path = require('node:path');
const os = require('node:os');
const { uninstallHook } = require(path.join(os.homedir(), '.aegis-gate', 'middleware', 'dist', 'installer.js'));

const SETTINGS_PATH = path.join(os.homedir(), '.claude', 'settings.json');

uninstallHook({ settingsPath: SETTINGS_PATH })
    .then(() => console.log('✓ Hook disabled. MCP tools (aegis_read etc) remain available.'))
    .catch(e => { console.error(`Error: ${e.message}`); process.exit(1); });
