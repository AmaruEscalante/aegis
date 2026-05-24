#!/usr/bin/env bash
# Stages repo-level assets inside middleware/ so `npm pack` / `npm publish`
# can include them. npm `files` cannot reference paths outside the package
# directory — entries like "../aegis/" are silently dropped. This script
# copies the runtime assets into middleware/ before pack, and is invoked by
# the package's `prepack` hook. The matching `postpack` script restores the
# working tree afterwards.
#
# Layout after copy (relative to middleware/):
#   middleware/aegis/         <- Python bridge + embedding + head/lr.joblib
#   middleware/skills/        <- /aegis slash-command skill
#   middleware/scripts/       <- hook-enforce.js
#   middleware/LICENSE
#   middleware/docs/PRIVACY.md
#
# NOTE: We intentionally do NOT overwrite middleware/README.md. That file is
# tracked in git (per T10) and is the dev-facing middleware doc. To publish a
# different README, we'd clobber a tracked file — which would dirty the
# working tree across npm publish runs. Keep them separate; the dev-facing
# middleware/README.md is what shows on npmjs.com. The marketplace-facing
# root README.md stays at the repo root.
#
# These staged copies are .gitignored (see middleware/.gitignore additions)
# so they don't pollute git history. `npm pack` picks them up via the local
# `files` entries in middleware/package.json.

set -euo pipefail

# This script lives at <repo>/scripts/copy-package-assets.sh; the package is at
# <repo>/middleware. Resolve both regardless of where the script is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PKG_DIR="$REPO_ROOT/middleware"

echo "[copy-package-assets] repo=$REPO_ROOT pkg=$PKG_DIR"

# Clean any previous staging so we don't ship stale files.
rm -rf "$PKG_DIR/aegis" "$PKG_DIR/skills" "$PKG_DIR/scripts" "$PKG_DIR/docs"
rm -f  "$PKG_DIR/LICENSE"

# Python runtime (bridge + embedding + trained head + requirements).
# Exclude __pycache__ to keep the tarball small.
mkdir -p "$PKG_DIR/aegis"
rsync -a --exclude '__pycache__' --exclude '*.pyc' \
    "$REPO_ROOT/aegis/" "$PKG_DIR/aegis/"

# Slash-command skill (skills/aegis/).
mkdir -p "$PKG_DIR/skills"
rsync -a --exclude '__pycache__' --exclude '*.pyc' \
    "$REPO_ROOT/skills/" "$PKG_DIR/skills/"

# Hook enforcer.
mkdir -p "$PKG_DIR/scripts"
cp "$REPO_ROOT/scripts/hook-enforce.js" "$PKG_DIR/scripts/hook-enforce.js"

# License (root). README is intentionally NOT touched — see header note.
cp "$REPO_ROOT/LICENSE" "$PKG_DIR/LICENSE"

# Privacy doc only (skip docs/eval-results, docs/plans, docs/superpowers, etc.).
mkdir -p "$PKG_DIR/docs"
cp "$REPO_ROOT/docs/PRIVACY.md" "$PKG_DIR/docs/PRIVACY.md"

echo "[copy-package-assets] done"
