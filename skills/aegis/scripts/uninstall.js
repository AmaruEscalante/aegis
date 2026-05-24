#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { uninstallHook } = require(path.join(os.homedir(), '.aegis-mcp', 'middleware', 'dist', 'installer.js'));

const SETTINGS_PATH = path.join(os.homedir(), '.claude', 'settings.json');
const CLAUDE_CONFIG_PATH = path.join(os.homedir(), '.claude.json');

async function main() {
    // 1. Remove hook from settings.json
    await uninstallHook({ settingsPath: SETTINGS_PATH });
    console.log('✓ Hook removed from ~/.claude/settings.json');

    // 2. Remove MCP server entry from .claude.json
    if (fs.existsSync(CLAUDE_CONFIG_PATH)) {
        const cfg = JSON.parse(fs.readFileSync(CLAUDE_CONFIG_PATH, 'utf8'));
        if (cfg.mcpServers?.aegis) {
            delete cfg.mcpServers.aegis;
            fs.writeFileSync(CLAUDE_CONFIG_PATH, JSON.stringify(cfg, null, 2) + '\n');
            console.log('✓ MCP server entry removed from ~/.claude.json');
        }
    }

    console.log('');
    console.log('Cache at ~/.aegis-mcp/ preserved (contains the cached Python venv and embedding model).');
    console.log('Remove it manually with `rm -rf ~/.aegis-mcp` if you no longer want Aegis on disk.');
    console.log('');
    console.log('Backups of ~/.claude/settings.json are under ~/.aegis-mcp/backups/.');
}

main().catch(e => { console.error(`Error: ${e.message}`); process.exit(1); });
