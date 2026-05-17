"""
Phase 2 eval — score the trained LR head on the 12 real samples/ files.

Same eval set Phase 1 used for gemma4:31b / gemma4:e2b / functiongemma / embeddinggemma-kNN,
so the resulting accuracy and macro-F1 are directly comparable to the existing scorecard rows.

Usage:
    .venv/bin/python train/eval_head.py
"""
from __future__ import annotations

import json
import pathlib
import statistics
import sys
import time
import urllib.request

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

# Re-use the 12 CASES from eval.py exactly, to keep the comparison apples-to-apples.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from eval import CASES, LABELS  # noqa: E402

OLLAMA_URL = "http://localhost:11434/api/embed"
HEAD_PATH = pathlib.Path("aegis-head/lr.joblib")


def embed_text(text: str, model: str) -> np.ndarray:
    payload = json.dumps({"model": model, "input": text}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
    return np.asarray(resp["embeddings"][0], dtype=np.float32)


def main() -> int:
    if not HEAD_PATH.exists():
        print(f"ERROR: {HEAD_PATH} not found. Run train/train_head.py first.", file=sys.stderr)
        return 1

    bundle = joblib.load(HEAD_PATH)
    model = bundle["model"]
    embed_model = bundle["embed_model"]
    print(f"Loaded head from {HEAD_PATH}")
    print(f"  embed_model:        {embed_model}")
    print(f"  classes:            {list(model.classes_)}")
    print(f"  trained-at C:       {bundle.get('C')}")
    print(f"  CV macro-F1 (train): {bundle['cv_results'][bundle['C']]['macro_f1_mean']:.4f}")

    # Warm-up call so the first eval timing isn't a cold-start artifact.
    _ = embed_text("warmup", embed_model)

    # --- Score each of the 12 cases
    y_true, y_pred, latencies = [], [], []
    print(f"\n{'file':50s}  {'true':>20s}  {'pred':>20s}  {'lat (ms)':>10}  {'ok':>4}")
    print("-" * 110)
    for path_str, true_label in CASES:
        path = pathlib.Path(path_str)
        text = path.read_text()
        t0 = time.perf_counter()
        vec = embed_text(text, embed_model)
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
