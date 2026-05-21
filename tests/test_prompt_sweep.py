"""Unit test for train/prompt_sweep.py's cv_score helper."""
from __future__ import annotations

import pathlib
import sys

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from train.prompt_sweep import cv_score


def test_cv_score_returns_all_four_metrics():
    """cv_score returns mean/std for both macro-F1 and accuracy."""
    rng = np.random.default_rng(42)
    X = rng.normal(size=(40, 8)).astype(np.float32)
    y = np.array(["a", "b", "c", "d"] * 10, dtype=object)
    scores = cv_score(X, y, C=1.0)
    assert set(scores.keys()) == {"mean_f1", "std_f1", "mean_acc", "std_acc"}
    for v in scores.values():
        assert isinstance(v, float)
