"""Validate eval_fresh.CASES structure + file existence + class balance."""
from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import eval_fresh

VALID_LABELS = {"classify_safe", "flag_pii", "block_transfer", "request_permission"}


def test_cases_is_nonempty_list_of_tuples():
    assert isinstance(eval_fresh.CASES, list)
    assert len(eval_fresh.CASES) >= 90
    for entry in eval_fresh.CASES:
        assert isinstance(entry, tuple) and len(entry) == 2


def test_every_case_file_exists():
    for path_str, _ in eval_fresh.CASES:
        p = REPO_ROOT / path_str
        assert p.exists(), f"missing: {path_str}"


def test_every_label_is_valid():
    for _, label in eval_fresh.CASES:
        assert label in VALID_LABELS


def test_class_balance_within_25():
    """Held-out is intentionally imbalanced — Channel C surfaces lots of safe and few internal docs.
    See samples/external/holdout_v2/README.md for the rationale.
    """
    from collections import Counter
    c = Counter(label for _, label in eval_fresh.CASES)
    assert set(c.keys()) == VALID_LABELS, f"missing class(es): {VALID_LABELS - set(c)}"
    min_count, max_count = min(c.values()), max(c.values())
    assert max_count - min_count <= 25, f"class imbalance > 25: {dict(c)}"


def test_no_overlap_with_existing_98_set():
    import eval as eval_original
    fresh_paths = {p for p, _ in eval_fresh.CASES}
    original_paths = {p for p, _ in eval_original.CASES}
    overlap = fresh_paths & original_paths
    assert not overlap, f"fresh held-out overlaps with original 98: {overlap}"
