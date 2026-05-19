"""
Phase 3b eval — score the trained LR head on the 30 real samples/ files.

Same eval set used across Phase 1-3, so results are directly comparable.

Usage:
    .venv/bin/python train/eval_head.py
"""
from __future__ import annotations

import pathlib
import statistics
import sys
import time

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

# Add repo root to import path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from aegis.embedding import Embedder  # noqa: E402
from eval import CASES, LABELS  # noqa: E402

HEAD_PATH = pathlib.Path("aegis-head/lr.joblib")


def main() -> int:
    if not HEAD_PATH.exists():
        print(f"ERROR: {HEAD_PATH} not found. Run train/train_head.py first.", file=sys.stderr)
        return 1

    bundle = joblib.load(HEAD_PATH)
    model = bundle["model"]
    embed_model = bundle["embed_model"]
    task_prompt = bundle.get("embed_task_prompt")
    if task_prompt is None:
        print(
            f"ERROR: head at {HEAD_PATH} predates Phase 3b (no embed_task_prompt field). "
            f"Retrain via train/train_head.py.",
            file=sys.stderr,
        )
        return 1
    if "embeddinggemma" not in embed_model.lower():
        print(f"ERROR: unexpected embed_model {embed_model!r}", file=sys.stderr)
        return 1

    embedder = Embedder(model_id=embed_model, default_task=task_prompt)
    print(f"Loaded head from {HEAD_PATH}")
    print(f"  embed_model:        {embed_model}")
    print(f"  embed_task_prompt:  {task_prompt}")
    print(f"  classes:            {list(model.classes_)}")
    print(f"  trained-at C:       {bundle.get('C')}")
    print(f"  CV macro-F1 (train): {bundle['cv_results'][bundle['C']]['macro_f1_mean']:.4f}")

    # --- Score each of the 30 cases
    y_true, y_pred, latencies = [], [], []
    print(f"\n{'file':50s}  {'true':>20s}  {'pred':>20s}  {'lat (ms)':>10}  {'ok':>4}")
    print("-" * 110)
    for path_str, true_label in CASES:
        path = pathlib.Path(path_str)
        text = path.read_text()
        t0 = time.perf_counter()
        vec = embedder.encode(text)
        pred = model.predict(vec.reshape(1, -1))[0]
        ms = (time.perf_counter() - t0) * 1000
        ok = "✓" if pred == true_label else "✗"
        print(f"{path.name:50s}  {true_label:>20s}  {pred:>20s}  {ms:>10.1f}  {ok:>4}")
        y_true.append(true_label)
        y_pred.append(pred)
        latencies.append(ms)

    # --- Aggregate metrics
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", labels=LABELS, zero_division=0)
    print("\n=== Aggregate metrics ===")
    print(f"  accuracy:      {acc:.4f}  ({sum(t==p for t,p in zip(y_true, y_pred))}/{len(y_true)})")
    print(f"  macro F1:      {macro_f1:.4f}")
    print(f"  warm p50 (ms): {statistics.median(latencies):.1f}")
    print(f"  warm p95 (ms): {sorted(latencies)[max(0, int(0.95*len(latencies))-1)]:.1f}")
    print(f"  warm max (ms): {max(latencies):.1f}")

    print("\n=== Per-class classification report ===")
    print(classification_report(y_true, y_pred, labels=LABELS, digits=4, zero_division=0))

    print("=== Confusion matrix (rows = true, cols = predicted) ===")
    cm = confusion_matrix(y_true, y_pred, labels=LABELS)
    w = max(len(lbl) for lbl in LABELS) + 2
    print(" " * w + " | " + " ".join(f"{lbl[:6]:>6}" for lbl in LABELS))
    print("-" * (w + 4 + 8 * len(LABELS)))
    for i, lbl in enumerate(LABELS):
        print(f"{lbl:<{w}} | " + " ".join(f"{n:>6d}" for n in cm[i]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
