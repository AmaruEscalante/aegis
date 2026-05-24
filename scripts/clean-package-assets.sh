#!/usr/bin/env bash
# Removes the staged copies that scripts/copy-package-assets.sh dropped into
# middleware/. Invoked by the package's `postpack` hook so `npm pack` and
# `npm publish` leave the working tree clean.
#
# This is symmetric with copy-package-assets.sh — same paths, just deleted.
# middleware/README.md is intentionally NOT touched (it's a tracked file,
# the copy script doesn't clobber it).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PKG_DIR="$REPO_ROOT/middleware"

echo "[clean-package-assets] cleaning staged copies in $PKG_DIR"

rm -rf "$PKG_DIR/aegis" "$PKG_DIR/skills" "$PKG_DIR/scripts" "$PKG_DIR/docs"
rm -f  "$PKG_DIR/LICENSE"

echo "[clean-package-assets] done"
