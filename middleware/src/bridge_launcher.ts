/**
 * Bridge launcher — detects Python, ensures the user-cached venv at
 * ~/.aegis-mcp/venv/ exists with pinned dependencies installed, spawns
 * aegis/bridge.py on an ephemeral port, and polls /health until ready.
 *
 * Owned by middleware/src/cli.ts; not invoked directly by the MCP server.
 */

import { spawn, spawnSync, ChildProcess } from 'node:child_process';
import { createServer } from 'node:net';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';

const REQUIRED_PYTHON_MIN = [3, 12] as const;

/**
 * Find a Python ≥3.12 interpreter on PATH. Tries `python3.12`, `python3`, `python` in order.
 * Throws with an install hint if nothing matches.
 */
export async function detectPython(): Promise<string> {
    // Try versioned binaries first (most likely to be ≥3.12), then fall back
    // to generic names. On macOS/Linux, `python3` is often an older system
    // Python (e.g. 3.9 on macOS), so versioned commands need to be checked
    // even if the spec lists `python3.12` only.
    const candidates = ['python3.12', 'python3.13', 'python3.14', 'python3.15', 'python3', 'python'];
    for (const cmd of candidates) {
        try {
            const result = spawnSync(cmd, ['-c', 'import sys; print(sys.version_info[0], sys.version_info[1])'], {
                encoding: 'utf8',
                timeout: 5000,
            });
            if (result.status === 0 && result.stdout) {
                const [maj, min] = result.stdout.trim().split(' ').map(Number);
                if (maj > REQUIRED_PYTHON_MIN[0] || (maj === REQUIRED_PYTHON_MIN[0] && min >= REQUIRED_PYTHON_MIN[1])) {
                    return cmd;
                }
            }
        } catch {
            // try next candidate
        }
    }
    throw new Error(
        `Aegis requires Python ${REQUIRED_PYTHON_MIN.join('.')}+ on PATH. ` +
        `Install via https://www.python.org/downloads/ or your system package manager.`
    );
}

/**
 * Return the Aegis cache directory at ~/.aegis-mcp/.
 * Creates it if it doesn't exist.
 */
export function resolveAegisCachePath(): string {
    const cachePath = path.join(os.homedir(), '.aegis-mcp');
    fs.mkdirSync(cachePath, { recursive: true });
    return cachePath;
}

/**
 * Find a free TCP port by binding to 0 and reading the assigned port.
 */
export async function findFreePort(): Promise<number> {
    return new Promise((resolve, reject) => {
        const server = createServer();
        server.unref();
        server.on('error', reject);
        server.listen(0, () => {
            const address = server.address();
            if (typeof address === 'object' && address !== null) {
                const port = address.port;
                server.close(() => resolve(port));
            } else {
                reject(new Error('Could not determine free port'));
            }
        });
    });
}

/**
 * Ensure a venv exists at <cachePath>/venv with the pinned deps installed.
 * Idempotent: if the venv exists and the requirements.txt mtime is older than
 * the venv's marker file, skip the install. Otherwise (re)install.
 */
export async function ensureVenv(
    pythonCmd: string,
    cachePath: string,
    requirementsPath: string,
): Promise<string> {
    const venvPath = path.join(cachePath, 'venv');
    const venvPython = path.join(venvPath, 'bin', 'python');
    const markerPath = path.join(venvPath, '.aegis-installed-marker');

    // Create venv if absent
    if (!fs.existsSync(venvPython)) {
        const r = spawnSync(pythonCmd, ['-m', 'venv', venvPath], { encoding: 'utf8' });
        if (r.status !== 0) {
            throw new Error(`Failed to create venv at ${venvPath}: ${r.stderr}`);
        }
    }

    // Check if (re)install is needed
    const reqMtime = fs.statSync(requirementsPath).mtime;
    const markerMtime = fs.existsSync(markerPath) ? fs.statSync(markerPath).mtime : new Date(0);
    if (reqMtime > markerMtime) {
        const r = spawnSync(venvPython, ['-m', 'pip', 'install', '--quiet', '-r', requirementsPath], {
            encoding: 'utf8',
        });
        if (r.status !== 0) {
            throw new Error(`Failed to install requirements: ${r.stderr}`);
        }
        fs.writeFileSync(markerPath, new Date().toISOString());
    }

    return venvPython;
}

/**
 * Spawn aegis/bridge.py and wait for /health to return OK.
 * Returns the child process handle (caller is responsible for killing on shutdown
 * via SIGTERM or SIGKILL).
 *
 * The default 10-minute timeout accommodates first-run downloads of the
 * embedding model (~150 MB from HF Hub). Subsequent runs return in ~1s once
 * the model is cached. Callers can pass a tighter timeout if they know the
 * model is already cached.
 */
export async function spawnBridge(
    venvPython: string,
    bridgeScript: string,
    port: number,
    timeoutMs = 600000,
): Promise<ChildProcess> {
    // The bridge script lives at <root>/aegis/bridge.py and does
    // `from aegis.embedding import Embedder`, which requires <root> on sys.path.
    // Python adds the script's own directory (aegis/) to sys.path[0] by default,
    // not its parent, so we explicitly put <root> on PYTHONPATH and set cwd
    // there for good measure.
    const bridgeRoot = path.dirname(path.dirname(bridgeScript));
    const child = spawn(venvPython, [bridgeScript, '--port', String(port), '--backend', 'local'], {
        stdio: ['ignore', 'pipe', 'pipe'],
        cwd: bridgeRoot,
        env: {
            ...process.env,
            PYTHONPATH: process.env.PYTHONPATH
                ? `${bridgeRoot}${path.delimiter}${process.env.PYTHONPATH}`
                : bridgeRoot,
        },
    });

    let stderr = '';
    child.stderr?.on('data', (d) => { stderr += d.toString(); });

    // Poll /health until ready or timeout
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        if (child.exitCode !== null) {
            throw new Error(`Bridge exited early (code ${child.exitCode}): ${stderr}`);
        }
        try {
            const res = await fetch(`http://127.0.0.1:${port}/health`);
            if (res.ok) {
                return child;
            }
        } catch {
            // not ready yet
        }
        await new Promise((r) => setTimeout(r, 500));
    }

    child.kill();
    throw new Error(`Bridge healthcheck timed out after ${timeoutMs}ms. stderr: ${stderr}`);
}
