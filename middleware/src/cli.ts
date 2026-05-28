#!/usr/bin/env node
/**
 * `npx aegis-gate` entry point.
 *
 * Subcommands:
 *   (default)        — install (with consent) + start MCP server
 *   install-hook     — re-install the enforcement hook
 *   uninstall        — remove hook + skill + MCP server config
 *   --version, -v    — print version
 *   --help, -h       — print help
 *
 * Env vars:
 *   AEGIS_INSTALL_HOOK=1   — auto-consent to hook install (for CI/scripts)
 *   AEGIS_INSTALL_HOOK=0   — skip hook install entirely
 */

import * as path from 'node:path';
import * as os from 'node:os';
import * as readline from 'node:readline';

import {
    detectPython,
    resolveAegisCachePath,
    ensureVenv,
    findFreePort,
    spawnBridge,
} from './bridge_launcher';
import { installHook, uninstallHook } from './installer';

export type CliCommand =
    | { command: 'run'; autoConsent?: boolean; skipHookInstall?: boolean }
    | { command: 'install-hook' }
    | { command: 'uninstall' }
    | { command: 'version' }
    | { command: 'help' };

export function parseArgs(
    argv: string[],
    env: Record<string, string | undefined> = process.env,
): CliCommand {
    if (argv.length === 0) {
        const hookEnv = env.AEGIS_INSTALL_HOOK;
        if (hookEnv === '0') return { command: 'run', skipHookInstall: true };
        if (hookEnv === '1') return { command: 'run', autoConsent: true };
        return { command: 'run' };
    }
    const cmd = argv[0];
    if (cmd === 'install-hook') return { command: 'install-hook' };
    if (cmd === 'uninstall') return { command: 'uninstall' };
    if (cmd === '--version' || cmd === '-v') return { command: 'version' };
    if (cmd === '--help' || cmd === '-h') return { command: 'help' };
    return { command: 'help' }; // unknown → help
}

const VERSION = '1.1.0';

const HELP_TEXT = `aegis-gate — on-device privacy gate for AI agents

Usage:
  npx aegis-gate                Install (with consent) + start MCP server
  npx aegis-gate install-hook   Re-install enforcement hook
  npx aegis-gate uninstall      Remove hook + MCP server config
  npx aegis-gate --version      Print version
  npx aegis-gate --help         Show this help

Environment:
  AEGIS_INSTALL_HOOK=1   Auto-consent to hook install (CI/scripts)
  AEGIS_INSTALL_HOOK=0   Skip hook install entirely

See https://github.com/AmaruEscalante/aegis for full documentation.
`;

async function promptConsent(): Promise<boolean> {
    const rl = readline.createInterface({ input: process.stdin, output: process.stderr });
    return new Promise((resolve) => {
        rl.question(
            'Add Aegis enforcement hook to ~/.claude/settings.json?\n' +
                '  This routes Read/Glob/Grep through aegis_read automatically.\n' +
                '  You can disable later with /aegis-disable-hook or `npx aegis-gate uninstall`.\n' +
                '[Y/n] ',
            (answer) => {
                rl.close();
                const normalized = answer.trim().toLowerCase();
                resolve(normalized === '' || normalized === 'y' || normalized === 'yes');
            },
        );
    });
}

async function runInstall(args: {
    autoConsent?: boolean;
    skipHookInstall?: boolean;
}): Promise<void> {
    process.stderr.write('Aegis Gate — on-device privacy gate for Claude Code\n\n');

    const settingsPath = path.join(os.homedir(), '.claude', 'settings.json');
    const hookScript = path.resolve(__dirname, '..', '..', 'scripts', 'hook-enforce.js');

    let shouldInstallHook = false;
    if (args.skipHookInstall) {
        process.stderr.write('Skipping hook install (AEGIS_INSTALL_HOOK=0).\n');
    } else if (args.autoConsent) {
        shouldInstallHook = true;
        process.stderr.write('Auto-consenting to hook install (AEGIS_INSTALL_HOOK=1).\n');
    } else {
        shouldInstallHook = await promptConsent();
    }

    if (shouldInstallHook) {
        const backup = await installHook({ settingsPath, hookScript });
        if (backup) {
            process.stderr.write(`  ✓ Hook installed (backup at ${backup})\n`);
        } else {
            process.stderr.write(`  ✓ Hook installed\n`);
        }
    }

    // Start the bridge
    const pythonCmd = await detectPython();
    const cachePath = resolveAegisCachePath();
    const requirementsPath = path.resolve(__dirname, '..', '..', 'aegis', 'requirements.txt');
    const bridgeScript = path.resolve(__dirname, '..', '..', 'aegis', 'bridge.py');

    process.stderr.write('Setting up Python environment...\n');
    const venvPython = await ensureVenv(pythonCmd, cachePath, requirementsPath);
    const port = await findFreePort();

    process.stderr.write(`Starting bridge on port ${port}...\n`);
    const bridge = await spawnBridge(venvPython, bridgeScript, port);

    process.stderr.write('Aegis ready.\n');

    // Graceful shutdown
    const shutdown = () => {
        process.stderr.write('Shutting down...\n');
        bridge.kill();
        process.exit(0);
    };
    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

    // Hand off to MCP server with the ephemeral port
    const { startMcpServer } = await import('./mcp-server');
    await startMcpServer({ bridgePort: port });
}

async function runUninstall(): Promise<void> {
    const settingsPath = path.join(os.homedir(), '.claude', 'settings.json');
    await uninstallHook({ settingsPath });
    process.stderr.write('  ✓ Aegis hook removed from ~/.claude/settings.json\n');
    process.stderr.write('Cache at ~/.aegis-gate/ preserved. Remove manually if desired.\n');
}

async function main(): Promise<void> {
    const args = parseArgs(process.argv.slice(2));

    switch (args.command) {
        case 'run':
            await runInstall(args);
            break;
        case 'install-hook': {
            const settingsPath = path.join(os.homedir(), '.claude', 'settings.json');
            const hookScript = path.resolve(__dirname, '..', '..', 'scripts', 'hook-enforce.js');
            const backup = await installHook({ settingsPath, hookScript });
            process.stderr.write(`  ✓ Hook installed (backup: ${backup ?? 'no prior config'})\n`);
            break;
        }
        case 'uninstall':
            await runUninstall();
            break;
        case 'version':
            console.log(VERSION);
            break;
        case 'help':
            console.log(HELP_TEXT);
            break;
    }
}

if (require.main === module) {
    main().catch((err) => {
        process.stderr.write(`Error: ${err.message}\n`);
        process.exit(1);
    });
}
