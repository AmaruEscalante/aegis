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
#   middleware/README.md      <- copied from repo root (marketplace-facing)
#   middleware/docs/PRIVACY.md
#
# NOTE: The marketplace-facing root README.md is copied into middleware/ so
# that npmjs.com shows the marketplace landing page. The dev-facing middleware
# doc lives at middleware/CONTRIBUTING.md (tracked in git). The copied
# README.md is .gitignored so it doesn't dirty the working tree.
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
rm -f  "$PKG_DIR/LICENSE" "$PKG_DIR/README.md"

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

# License (root).
cp "$REPO_ROOT/LICENSE" "$PKG_DIR/LICENSE"

# Copy root README.md into middleware/ for npm tarball (marketplace-facing).
# The dev-facing doc lives at middleware/CONTRIBUTING.md.
cp "$REPO_ROOT/README.md" "$PKG_DIR/README.md"

# Privacy doc only (skip docs/eval-results, docs/plans, docs/superpowers, etc.).
mkdir -p "$PKG_DIR/docs"
cp "$REPO_ROOT/docs/PRIVACY.md" "$PKG_DIR/docs/PRIVACY.md"

echo "[copy-package-assets] done"
