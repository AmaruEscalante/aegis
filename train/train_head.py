"""
Phase 3b — train an LR classifier head on top of frozen EmbeddingGemma.

Pipeline:
    1. Read train/dataset.jsonl  (200 hand-curated examples)
    2. Embed each row via the in-process Embedder (task-prompted)    -> X (200, 768)
    3. Fit sklearn LogisticRegression                                  -> trained head
    4. Save the head to aegis-head/lr.joblib
    5. Evaluate on the 12 real samples/ files                          -> scorecard row

Usage:
    .venv/bin/python train/train_head.py

Requires:
    - HF Hub access (google/embeddinggemma-300m cached or downloadable).
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score

# Add repo root to import path so `aegis.embedding` resolves when running from train/
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from aegis.embedding import Embedder  # noqa: E402

# ── Config ──────────────────────────────────────────────────────────
DATASET_PATH = pathlib.Path("train/dataset.jsonl")
HEAD_PATH = pathlib.Path("aegis-head/lr.joblib")
WINNER_PATH = pathlib.Path("train/sweep_winner.json")
EMBED_DIM = 768
RANDOM_SEED = 42
DEFAULT_C_GRID = [0.1, 1.0, 10.0]
VALID_PROMPTS = ("none", "classification", "classify_short", "classify_doc")


def _parse_args() -> tuple[str, float, bool]:
    """Resolve (prompt, C, dry_run) from CLI flags or sweep_winner.json.

    Resolution order:
      1. Explicit --prompt / --C flags
      2. train/sweep_winner.json (if present)
      3. Error
    """
    import argparse
    parser = argparse.ArgumentParser(description="Train the Aegis LR head.")
    parser.add_argument("--prompt", choices=VALID_PROMPTS, default=None,
                        help="Task-prompt variant (overrides sweep_winner.json).")
    parser.add_argument("--C", type=float, default=None,
                        help="Regularization strength (overrides sweep_winner.json).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print resolved (prompt, C) and exit without training.")
    args = parser.parse_args()

    prompt: str | None = args.prompt
    C: float | None = args.C

    if prompt is None or C is None:
        if WINNER_PATH.exists():
            try:
                winner = json.loads(WINNER_PATH.read_text())
            except (json.JSONDecodeError, OSError) as e:
                print(f"ERROR: failed to read {WINNER_PATH}: {e}", file=sys.stderr)
                sys.exit(2)
            if prompt is None:
                prompt = winner.get("prompt")
            if C is None:
                C = winner.get("C")

    if prompt is None or C is None:
        print(
            "ERROR: must supply --prompt and --C, or run train/prompt_sweep.py first to\n"
            f"produce {WINNER_PATH} (consumed automatically when flags are omitted).",
            file=sys.stderr,
        )
        sys.exit(2)

    if prompt not in VALID_PROMPTS:
        print(f"ERROR: invalid prompt {prompt!r}; valid: {VALID_PROMPTS}", file=sys.stderr)
        sys.exit(2)

    return prompt, float(C), args.dry_run


def _build_cv_results(winner_data: dict | None, selected_prompt: str, selected_C: float) -> dict:
    """Build the legacy {C: {macro_f1_mean: ..., ...}} dict from sweep_winner.json data.

    Filters all_results to entries matching the selected prompt. If winner_data is None
    or has no entries for the prompt, returns a single stub entry keyed by selected_C
    so downstream lookups like `bundle['cv_results'][bundle['C']]['macro_f1_mean']`
    continue to work in a degraded state (the stub returns None for the metric).
    """
    out: dict[float, dict] = {}
    if winner_data:
        for entry in winner_data.get("all_results", []):
            if entry["prompt"] == selected_prompt:
                out[float(entry["C"])] = {
                    "macro_f1_mean": entry["mean_f1"],
                    "macro_f1_std": entry["std_f1"],
                    "accuracy_mean": entry["mean_acc"],
                    "accuracy_std": entry["std_acc"],
                }
    if not out:
        out[selected_C] = {
            "macro_f1_mean": None,
            "note": "no sweep_winner.json available; metrics not recorded",
        }
    return out


# Resolved at module load via _parse_args() in __main__
TASK_PROMPT: str = "none"  # placeholder; real value set at runtime
SELECTED_C: float = 1.0     # placeholder; real value set at runtime

_EMBEDDER: Embedder | None = None


def _get_embedder() -> Embedder:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = Embedder(default_task=TASK_PROMPT)
    return _EMBEDDER


def embed_text(text: str) -> np.ndarray:
    """Embed via the shared in-process Embedder. Returns (768,) float32."""
    return _get_embedder().encode(text, task=TASK_PROMPT)


# ── Step B: embedding the whole training set ────────────────────────
def embed_dataset(jsonl_path: pathlib.Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load dataset.jsonl, embed every row, return (X, y, ids)."""
    rows = [json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()]
    print(f"Loaded {len(rows)} rows from {jsonl_path}")

    X = np.zeros((len(rows), EMBED_DIM), dtype=np.float32)
    y = np.empty(len(rows), dtype=object)
    ids = []

    t_start = time.perf_counter()
    for i, row in enumerate(rows):
        t0 = time.perf_counter()
        X[i] = embed_text(row["text"])
        y[i] = row["label"]
        ids.append(row["scenario_id"])
        ms = (time.perf_counter() - t0) * 1000
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  [{i+1:3d}/{len(rows)}]  {row['scenario_id']:28s}  {ms:6.0f} ms")
    total_s = time.perf_counter() - t_start
    print(f"Embedded {len(rows)} rows in {total_s:.1f}s  ({total_s/len(rows)*1000:.0f} ms/row avg)")

    return X, y, ids


# ── Step C: train + cross-validate the LR head ──────────────────────
def build_lr(C: float) -> LogisticRegression:
    """Construct an LR estimator with a given regularization strength."""
    # NOTE: sklearn>=1.7 auto-selects multinomial softmax whenever >2 classes are present;
    # the `multi_class` kwarg is deprecated/removed. We rely on that default behavior here.
    return LogisticRegression(
        C=C,
        max_iter=2000,
        solver="lbfgs",
        random_state=RANDOM_SEED,
    )


def sweep_C_with_cv(X: np.ndarray, y: np.ndarray, C_values: list[float]) -> tuple[float, dict]:
    """Run 5-fold stratified CV at each C; return the best C and the full results table."""
    kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    results: dict[float, dict] = {}
    print("\n=== 5-fold cross-validation sweep over C ===")
    print(f"{'C':>8} | {'mean acc':>10} | {'std':>6} | {'mean macro-F1':>14}")
    print("-" * 50)
    for C in C_values:
        model = build_lr(C)
        accs = cross_val_score(model, X, y, cv=kf, scoring="accuracy")
        f1s  = cross_val_score(model, X, y, cv=kf, scoring="f1_macro")
        results[C] = {
            "accuracy_mean": float(accs.mean()),
            "accuracy_std":  float(accs.std()),
            "macro_f1_mean": float(f1s.mean()),
            "macro_f1_std":  float(f1s.std()),
        }
        print(f"{C:>8.2f} | {accs.mean():>10.4f} | {accs.std():>6.4f} | {f1s.mean():>14.4f}")

    best_C = max(C_values, key=lambda c: results[c]["macro_f1_mean"])
    print(f"\nBest C by macro-F1: {best_C}")
    return best_C, results


def fit_final(X: np.ndarray, y: np.ndarray, C: float) -> LogisticRegression:
    """Fit the final head on the full training set at the chosen C."""
    print(f"\n=== Fitting final LR head on all 200 examples at C={C} ===")
    t0 = time.perf_counter()
    model = build_lr(C).fit(X, y)
    print(f"Fit completed in {(time.perf_counter()-t0)*1000:.0f} ms")
    print(f"Learned weights: coef_ shape={model.coef_.shape}, intercept_ shape={model.intercept_.shape}")
    print(f"Total learned parameters: {model.coef_.size + model.intercept_.size}")
    print(f"Classes (in order): {list(model.classes_)}")

    # Training accuracy + per-class report (will be optimistic — fit-on-self)
    y_pred = model.predict(X)
    print("\nTraining-set classification report (optimistic — fit on these):")
    print(classification_report(y, y_pred, digits=4))
    print("Training-set confusion matrix:")
    print_confusion_matrix(y, y_pred, model.classes_)
    return model


def print_confusion_matrix(y_true, y_pred, classes):
    cm = confusion_matrix(y_true, y_pred, labels=classes)
    w = max(len(c) for c in classes) + 2
    header = " " * w + " | " + " ".join(f"{c[:6]:>6}" for c in classes)
    print(header)
    print("-" * len(header))
    for i, c in enumerate(classes):
        row = f"{c:<{w}} | " + " ".join(f"{n:>6d}" for n in cm[i])
        print(row)


# ── Entry point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    TASK_PROMPT, SELECTED_C, DRY_RUN = _parse_args()

    if DRY_RUN:
        # Print resolved config and exit — used by tests + sanity checks.
        print(json.dumps({"prompt": TASK_PROMPT, "C": SELECTED_C}, indent=2))
        sys.exit(0)

    if not DATASET_PATH.exists():
        print(f"ERROR: {DATASET_PATH} not found. Run `python3 train/curated_data.py` first.", file=sys.stderr)
        sys.exit(1)

    # --- Embed
    X, y, ids = embed_dataset(DATASET_PATH)

    # Sanity prints
    print(f"\nX shape: {X.shape}    dtype: {X.dtype}")
    print(f"y shape: {y.shape}    classes: {sorted(set(y))}")
    print(f"per-class count: {dict((c, int((y == c).sum())) for c in sorted(set(y)))}")
    norms = np.linalg.norm(X, axis=1)
    print(f"L2 norms: min={norms.min():.4f}  mean={norms.mean():.4f}  max={norms.max():.4f}")

    # --- Skip the CV sweep — the prompt_sweep step already selected (prompt*, C*).
    print(f"\n=== Fitting head at prompt={TASK_PROMPT!r}, C={SELECTED_C} (chosen upstream) ===")
    model = fit_final(X, y, SELECTED_C)

    # --- Save
    winner_data: dict | None = None
    if WINNER_PATH.exists():
        try:
            winner_data = json.loads(WINNER_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            winner_data = None
    cv_results = _build_cv_results(winner_data, TASK_PROMPT, SELECTED_C)

    bundle = {
        "model": model,
        "embed_model": Embedder.DEFAULT_MODEL_ID,
        "embed_task_prompt": TASK_PROMPT,
        "C": SELECTED_C,
        "cv_results": cv_results,
        "training_set_phase": "3b.5",
        "training_set_size": int(X.shape[0]),
        "trained_at": time.strftime("%Y-%m-%d"),
        "selection_source": "prompt_sweep.py CV winner" if WINNER_PATH.exists() else "manual flags",
    }
    HEAD_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, HEAD_PATH)
    print(f"\nSaved trained head to {HEAD_PATH}  ({HEAD_PATH.stat().st_size/1024:.1f} KB)")
    for k in ("embed_model", "embed_task_prompt", "C", "training_set_phase", "training_set_size", "trained_at"):
        print(f"  {k}: {bundle[k]}")
