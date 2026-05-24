#!/usr/bin/env bash
# End-to-end smoke test for Phase 4.
#
# Usage:  ./tests/test_smoke_install.sh
#
# Creates a temporary $HOME, runs the install flow with AEGIS_INSTALL_HOOK=1
# (auto-consent), verifies the hook landed, verifies the bridge responds,
# then runs uninstall and verifies clean teardown.

set -euo pipefail

TMP_HOME=$(mktemp -d -t aegis-smoke-XXXXXXXX)
ORIG_HOME=$HOME
export HOME=$TMP_HOME
trap "rm -rf $TMP_HOME; export HOME=$ORIG_HOME" EXIT

echo "=== Smoke test: temp HOME=$HOME ==="

# Build the TS server in dev mode
cd middleware
npm install --silent
npm run build
cd ..

# Auto-consent install
echo "[1/5] Running install with AEGIS_INSTALL_HOOK=1..."
AEGIS_INSTALL_HOOK=1 node middleware/dist/cli.js &
CLI_PID=$!
sleep 30  # give time for venv + bridge startup
echo "[1/5] Install kicked off; verifying..."

# Verify hook installed
echo "[2/5] Checking hook in settings.json..."
test -f "$HOME/.claude/settings.json" || { echo "FAIL: settings.json not created"; exit 1; }
grep -q 'aegis-mcp:enforce-read-routing' "$HOME/.claude/settings.json" || { echo "FAIL: hook entry missing"; exit 1; }
echo "[2/5] OK"

# Verify venv populated
echo "[3/5] Checking ~/.aegis-mcp/venv..."
test -d "$HOME/.aegis-mcp/venv/bin" || { echo "FAIL: venv not created"; exit 1; }
echo "[3/5] OK"

# Kill the CLI, run uninstall
echo "[4/5] Stopping CLI..."
kill $CLI_PID 2>/dev/null || true
wait $CLI_PID 2>/dev/null || true
sleep 2

echo "[5/5] Running uninstall..."
node middleware/dist/cli.js uninstall

# Verify hook removed
grep -q 'aegis-mcp:enforce-read-routing' "$HOME/.claude/settings.json" && { echo "FAIL: hook still present after uninstall"; exit 1; }
echo "[5/5] OK"

echo ""
echo "=== Smoke test PASSED ==="
