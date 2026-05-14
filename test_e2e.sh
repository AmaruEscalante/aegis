#!/usr/bin/env bash
# ============================================================================
# End-to-End Test: Aegis Bridge + TypeScript Middleware
# ============================================================================
# Starts the Python bridge server, waits for it to be ready, runs the
# TypeScript e2e tests against real sample files, then cleans up.
#
# Usage:
#   ./test_e2e.sh                          # run e2e tests
#   ./test_e2e.sh --skip-bridge            # assume bridge is already running
#
# Prerequisites:
#   - uv sync (Python deps)
#   - npm install (in middleware/)
#   - aegis-adapter/ model directory present
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRIDGE_PID=""
PORT=7523
SKIP_BRIDGE=false

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --skip-bridge) SKIP_BRIDGE=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

cleanup() {
  if [[ -n "$BRIDGE_PID" ]]; then
    echo ""
    echo "[e2e] Stopping bridge (PID $BRIDGE_PID)..."
    kill "$BRIDGE_PID" 2>/dev/null || true
    wait "$BRIDGE_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "============================================"
echo "  Aegis End-to-End Test"
echo "============================================"
echo "  Port:     $PORT"
echo ""

# --- Step 1: Start the bridge ---
if [[ "$SKIP_BRIDGE" == "false" ]]; then
  echo "[e2e] Starting Aegis bridge server..."
  cd "$SCRIPT_DIR"

  uv run python aegis_bridge.py \
    --port "$PORT" &
  BRIDGE_PID=$!

  # Wait for the bridge to be ready (poll /health)
  echo "[e2e] Waiting for bridge to be ready..."
  for i in $(seq 1 60); do
    if curl -s "http://127.0.0.1:$PORT/health" > /dev/null 2>&1; then
      echo "[e2e] Bridge ready! (took ~${i}s)"
      break
    fi
    if ! kill -0 "$BRIDGE_PID" 2>/dev/null; then
      echo "[e2e] ERROR: Bridge process died during startup."
      exit 1
    fi
    sleep 1
  done

  # Final health check
  HEALTH=$(curl -s "http://127.0.0.1:$PORT/health" 2>/dev/null || echo '{"status":"unreachable"}')
  echo "[e2e] Bridge health: $HEALTH"
  echo ""
else
  echo "[e2e] Skipping bridge startup (--skip-bridge)"
  HEALTH=$(curl -s "http://127.0.0.1:$PORT/health" 2>/dev/null || echo '{"status":"unreachable"}')
  echo "[e2e] Bridge health: $HEALTH"
  echo ""
fi

# --- Step 2: Quick bridge smoke test ---
echo "[e2e] Smoke test: classifying a safe summary..."
CLASSIFY_RESULT=$(curl -s -X POST "http://127.0.0.1:$PORT/classify" \
  -H "Content-Type: application/json" \
  -d '{"text": "A marketing blog post about new product features. No personal data, no API keys, no credentials."}' \
  2>/dev/null || echo '{"error":"bridge unreachable"}')
echo "[e2e] Classify result: $CLASSIFY_RESULT"
echo ""

echo "[e2e] Smoke test: classifying a secrets summary..."
CLASSIFY_RESULT=$(curl -s -X POST "http://127.0.0.1:$PORT/classify" \
  -H "Content-Type: application/json" \
  -d '{"text": "Kubernetes secrets YAML file with base64-encoded production credentials including STRIPE_SECRET_KEY, DATABASE_URL with admin password, and AWS access keys."}' \
  2>/dev/null || echo '{"error":"bridge unreachable"}')
echo "[e2e] Classify result: $CLASSIFY_RESULT"
echo ""

# --- Step 3: Run TypeScript e2e tests ---
echo "[e2e] Running TypeScript e2e tests..."
echo ""
cd "$SCRIPT_DIR/middleware"
npx vitest run tests/e2e.test.ts 2>&1

echo ""
echo "[e2e] Done!"
