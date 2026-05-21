"""Phase 3b.5 — fresh held-out eval set (~107 samples).

This module is touched EXACTLY ONCE for the headline Phase 3b.5 accuracy
number. Re-running it after gate decision reuses the held-out and invalidates
the single-shot guarantee. If you find yourself wanting to re-run, stop and
add the failing case to eval_regression.py instead.

Generated 2026-05-21 from:
  - 82 Channel C mined files in samples/external/holdout_v2/
  - 25 Channel A hand-curated files in samples/holdout_v2/

Provenance for each Channel C file lives in its sibling .provenance.json.
The class distribution is intentionally imbalanced — see
samples/external/holdout_v2/README.md for the rationale.
"""
from __future__ import annotations

import json
import pathlib

LABELS = ("classify_safe", "flag_pii", "block_transfer", "request_permission")


def _discover_cases() -> list[tuple[str, str]]:
    """Walk holdout_v2/ subtrees and emit (relative_path, label) tuples."""
    cases: list[tuple[str, str]] = []
    repo_root = pathlib.Path(__file__).resolve().parent

    # Channel C: samples/external/holdout_v2/<label>/<file>
    for label_dir in (repo_root / "samples" / "external" / "holdout_v2").iterdir():
        if not label_dir.is_dir():
            continue
        label = label_dir.name
        if label not in LABELS:
            continue
        for f in sorted(label_dir.iterdir()):
            if not f.is_file():
                continue
            if f.name.endswith(".provenance.json"):
                continue
            if f.name == "README.md":
                continue
            rel = f.relative_to(repo_root).as_posix()
            cases.append((rel, label))

    # Channel A: samples/holdout_v2/<file> — label encoded in _labels.json manifest
    manifest_path = repo_root / "samples" / "holdout_v2" / "_labels.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for fname, label in manifest.items():
            f = repo_root / "samples" / "holdout_v2" / fname
            if f.is_file():
                cases.append((f.relative_to(repo_root).as_posix(), label))

    return sorted(cases)


CASES = _discover_cases()
