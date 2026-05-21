"""Unit tests for train/train_head.py CLI argument handling."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAIN_SCRIPT = REPO_ROOT / "train" / "train_head.py"
PY = REPO_ROOT / ".venv" / "bin" / "python"


def test_help_lists_new_args():
    """--help mentions both --prompt and --C."""
    result = subprocess.run(
        [str(PY), str(TRAIN_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--prompt" in result.stdout
    assert "--C" in result.stdout


def test_missing_both_args_and_winner_file_errors_clearly(tmp_path, monkeypatch):
    """If no --prompt/--C AND no sweep_winner.json, exit nonzero with helpful message."""
    # Run from a fresh cwd so train/sweep_winner.json isn't found
    result = subprocess.run(
        [str(PY), str(TRAIN_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode != 0
    err = (result.stderr + result.stdout).lower()
    assert "prompt" in err and "sweep_winner.json" in err


def test_winner_file_consumed_when_flags_absent(tmp_path):
    """If train/sweep_winner.json exists and flags are absent, it's read."""
    # Build a minimal sweep_winner.json in tmp_path/train/
    train_dir = tmp_path / "train"
    train_dir.mkdir()
    winner = {"prompt": "none", "C": 1.0}
    (train_dir / "sweep_winner.json").write_text(json.dumps(winner))

    # We can't actually run the full training pipeline here (needs HF model).
    # Instead, invoke train_head.py in a --dry-run mode that prints the resolved
    # (prompt, C) without doing any model work.
    result = subprocess.run(
        [str(PY), str(TRAIN_SCRIPT), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert '"prompt": "none"' in result.stdout or "prompt=none" in result.stdout
    assert '"C": 1.0' in result.stdout or "C=1.0" in result.stdout


def test_explicit_flags_override_winner_file(tmp_path):
    """If both --prompt and the winner file exist, --prompt wins."""
    train_dir = tmp_path / "train"
    train_dir.mkdir()
    (train_dir / "sweep_winner.json").write_text(json.dumps({"prompt": "classify_doc", "C": 10.0}))

    result = subprocess.run(
        [str(PY), str(TRAIN_SCRIPT), "--prompt", "none", "--C", "1.0", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert '"prompt": "none"' in out or "prompt=none" in out
    assert '"C": 1.0' in out or "C=1.0" in out


def test_build_cv_results_with_sweep_data():
    """_build_cv_results filters by prompt and reshapes to legacy {C: {...}} dict."""
    sys.path.insert(0, str(REPO_ROOT))
    from train.train_head import _build_cv_results

    winner_data = {
        "all_results": [
            {"prompt": "none", "C": 0.1, "mean_f1": 0.90, "std_f1": 0.01, "mean_acc": 0.91, "std_acc": 0.02},
            {"prompt": "none", "C": 1.0, "mean_f1": 0.95, "std_f1": 0.01, "mean_acc": 0.96, "std_acc": 0.02},
            {"prompt": "classify_doc", "C": 1.0, "mean_f1": 0.80, "std_f1": 0.05, "mean_acc": 0.82, "std_acc": 0.04},
        ]
    }
    result = _build_cv_results(winner_data, "none", 1.0)
    assert set(result.keys()) == {0.1, 1.0}
    assert result[1.0]["macro_f1_mean"] == 0.95


def test_build_cv_results_with_no_sweep_data():
    """_build_cv_results returns a stub when sweep data is absent."""
    sys.path.insert(0, str(REPO_ROOT))
    from train.train_head import _build_cv_results

    result = _build_cv_results(None, "none", 1.0)
    assert 1.0 in result
    assert result[1.0]["macro_f1_mean"] is None
