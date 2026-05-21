"""Validate eval_regression.CASES + presence of the 5 Phase 3b failures."""
from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import eval_regression

VALID_LABELS = {"classify_safe", "flag_pii", "block_transfer", "request_permission"}

PHASE_3B_FAILURES = {
    "samples/external/flag_pii/delphix_dxtoolkit_f6fdab90.example",
    "samples/external/flag_pii/AgrawalVi_ponovo_83908028.csv",
    "samples/external/block_transfer/owid_owid-grapher_b8fa04ba.example-full",
    "samples/hr_exit_interview_records.txt",
    "samples/saas_help_center_article.md",
}


def test_cases_is_list_of_tuples():
    assert isinstance(eval_regression.CASES, list)
    for entry in eval_regression.CASES:
        assert isinstance(entry, tuple) and len(entry) == 2


def test_all_five_phase_3b_failures_present():
    paths = {p for p, _ in eval_regression.CASES}
    missing = PHASE_3B_FAILURES - paths
    assert not missing, f"missing Phase 3b failures: {missing}"


def test_every_case_file_exists():
    for path_str, _ in eval_regression.CASES:
        p = REPO_ROOT / path_str
        assert p.exists(), f"missing: {path_str}"


def test_every_label_is_valid():
    for _, label in eval_regression.CASES:
        assert label in VALID_LABELS
