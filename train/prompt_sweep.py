"""Phase 3b T7d — prompt sweep on training-set CV (selection step).

For each (prompt, C) combination, embed the 200 training samples with that
prompt, run 5-fold stratified CV, and report mean / std macro-F1.

The 100-sample held-out eval set is INTENTIONALLY UNTOUCHED here.
Selection signal: CV macro-F1 only.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from aegis.embedding import Embedder  # noqa: E402

DATASET_PATH = pathlib.Path("train/dataset.jsonl")
EMBED_DIM = 768
RANDOM_SEED = 42
C_GRID = [0.1, 1.0, 10.0]
PROMPT_GRID = ["none", "classify_short", "classify_doc", "classification"]


def load_dataset() -> tuple[list[str], np.ndarray]:
    rows = [json.loads(line) for line in DATASET_PATH.read_text().splitlines() if line.strip()]
    texts = [r["text"] for r in rows]
    y = np.array([r["label"] for r in rows], dtype=object)
    return texts, y


def embed_with_prompt(texts: list[str], task: str) -> np.ndarray:
    """Embed all texts with the given task prompt. Returns (N, 768) float32."""
    embedder = Embedder(default_task=task)
    t0 = time.perf_counter()
    X = embedder.encode_batch(texts, task=task, batch_size=32)
    dt = time.perf_counter() - t0
    print(f"  embedded {len(texts)} rows in {dt:.1f}s")
    return X


def cv_score(X: np.ndarray, y: np.ndarray, C: float) -> tuple[float, float]:
    """5-fold stratified CV macro-F1 for the given C."""
    kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    model = LogisticRegression(C=C, max_iter=2000, solver="lbfgs", random_state=RANDOM_SEED)
    scores = cross_val_score(model, X, y, cv=kf, scoring="f1_macro")
    return float(scores.mean()), float(scores.std())


def main() -> int:
    if not DATASET_PATH.exists():
        print(f"ERROR: {DATASET_PATH} not found. Run train/curated_data.py first.", file=sys.stderr)
        return 1

    print(f"Loading training set from {DATASET_PATH}")
    texts, y = load_dataset()
    print(f"  {len(texts)} rows, classes: {sorted(set(y.tolist()))}\n")

    results: dict[tuple[str, float], tuple[float, float]] = {}
    for prompt in PROMPT_GRID:
        print(f"=== Prompt: {prompt!r} ({Embedder.DEFAULT_PROMPTS[prompt]!r}) ===")
        X = embed_with_prompt(texts, prompt)
        for C in C_GRID:
            mean_f1, std_f1 = cv_score(X, y, C)
            results[(prompt, C)] = (mean_f1, std_f1)
            print(f"  C={C:>6.2f}  CV macro-F1 = {mean_f1:.4f} ± {std_f1:.4f}")
        print()

    print("\n=== Sweep summary (sorted by CV macro-F1 desc) ===")
    print(f"{'rank':>4} | {'prompt':>16} | {'C':>6} | {'mean F1':>9} | {'std':>6}")
    print("-" * 60)
    sorted_results = sorted(results.items(), key=lambda kv: kv[1][0], reverse=True)
    for rank, ((prompt, C), (m, s)) in enumerate(sorted_results, start=1):
        print(f"{rank:>4} | {prompt:>16} | {C:>6.2f} | {m:>9.4f} | {s:>6.4f}")

    best_prompt, best_C = sorted_results[0][0]
    best_mean, best_std = sorted_results[0][1]
    print(f"\nWinner: prompt={best_prompt!r}, C={best_C}, CV macro-F1 = {best_mean:.4f} ± {best_std:.4f}")

    # Sanity check: report tie-breaking if anything is within 0.005 of the winner.
    near_ties = [r for r in sorted_results if r[1][0] >= best_mean - 0.005 and r != sorted_results[0]]
    if near_ties:
        print(f"\nNear-ties (within 0.005 of winner — consider preferring simpler prompt):")
        for (prompt, C), (m, s) in near_ties:
            print(f"  prompt={prompt!r}, C={C}, F1 = {m:.4f} ± {s:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
