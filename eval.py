"""
Generalized eval runner for Aegis base models.

Runs one model through the eval set (12 hand-curated real samples in samples/),
reports per-class P/R/F1, accuracy, macro F1, confusion matrix, and warm-call
latency p50/p95/p99 (cold-start reported separately).

Supports two protocols:
  - bridge: POST to a running aegis_bridge.py /classify (generative models)
  - knn:    POST to Ollama /api/embed directly, k-NN against labeled set (embeddings)

Usage:
    # Generative model via bridge (bridge must already be running with --model <tag>)
    python eval.py --model gemma4:31b --protocol bridge

    # Embedding model directly (no bridge needed)
    python eval.py --model embeddinggemma --protocol knn

    # Auto-detect: if model name contains "embed", use knn; else bridge.
    python eval.py --model embeddinggemma   # -> knn
    python eval.py --model gemma4:e2b        # -> bridge

Output:
    docs/eval-results/<YYYY-MM-DD>-<model-tag>-base.txt
"""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

# Optional numpy — only needed for the knn protocol. Import lazily.
def _import_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        print("ERROR: numpy is required for --protocol knn. Run via `uv run python eval.py ...`.", file=sys.stderr)
        sys.exit(1)


# Hand-curated samples — must match what existed for Phase 0.
CASES = [
    ("samples/open_source_readme.md",      "classify_safe"),
    ("samples/marketing_copy.txt",         "classify_safe"),
    ("samples/blog_post_draft.txt",        "classify_safe"),
    ("samples/patient_records.csv",        "flag_pii"),
    ("samples/employee_directory.json",    "flag_pii"),
    ("samples/user_database.json",         "flag_pii"),
    ("samples/api_config.env",             "block_transfer"),
    ("samples/kubernetes_secrets.yaml",    "block_transfer"),
    ("samples/docker_compose_prod.yml",    "block_transfer"),
    ("samples/vendor_evaluation.txt",      "request_permission"),
    ("samples/partnership_agreement.txt",  "request_permission"),
    ("samples/board_meeting_minutes.txt",  "request_permission"),
]

LABELS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]

DEFAULT_BRIDGE_URL = "http://127.0.0.1:7523"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
MAX_INPUT_CHARS = 8000


# ── Per-protocol classifiers ─────────────────────────────────────────────────

def classify_via_bridge(bridge_url: str, text: str) -> tuple[str, float, float]:
    """Return (predicted_tool, confidence, wall_ms)."""
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{bridge_url}/classify",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    wall_ms = (time.time() - start) * 1000
    tool = data.get("tool", "request_permission")
    confidence = float(data.get("confidence", 0.0))
    return tool, confidence, wall_ms


def embed_text(ollama_url: str, model: str, text: str):
    """Call Ollama /api/embed and return (embedding_vector, wall_ms)."""
    payload = json.dumps({"model": model, "input": text[:MAX_INPUT_CHARS]}).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    wall_ms = (time.time() - start) * 1000
    np = _import_numpy()
    return np.array(data["embeddings"][0], dtype=np.float32), wall_ms


# ── Metrics ──────────────────────────────────────────────────────────────────

def f1_for_class(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def percentile(values: list[float], p: float) -> float:
    """p in [0, 100]. Returns NaN-like value (0.0) if values is empty."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


# ── Main ─────────────────────────────────────────────────────────────────────

def auto_protocol(model: str) -> str:
    """Heuristic: model names containing 'embed' use knn, otherwise bridge."""
    return "knn" if "embed" in model.lower() else "bridge"


def load_eval_texts() -> list[tuple[str, str, str]]:
    """Return [(path, label, text)] for every CASE. Skip missing files with a warning."""
    out = []
    for path, label in CASES:
        try:
            with open(path, "r", errors="replace") as f:
                text = f.read()
            out.append((path, label, text))
        except OSError as e:
            print(f"WARNING: skipping {path}: {e}", file=sys.stderr)
    return out


def main():
    parser = argparse.ArgumentParser(description="Aegis eval runner")
    parser.add_argument("--model", required=True, help="Ollama model tag (e.g., gemma4:e2b, embeddinggemma)")
    parser.add_argument(
        "--protocol",
        choices=["bridge", "knn", "auto"],
        default="auto",
        help="bridge = POST to running aegis_bridge.py /classify; knn = direct Ollama /api/embed + k-NN LOO-CV",
    )
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument(
        "--warmup-calls",
        type=int,
        default=1,
        help="Throwaway calls before timing (default 1)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/eval-results"),
        help="Where to write the per-model log",
    )
    args = parser.parse_args()

    protocol = auto_protocol(args.model) if args.protocol == "auto" else args.protocol
    print(f"[eval] model={args.model} protocol={protocol}")

    cases = load_eval_texts()
    if len(cases) < 4:
        print(f"ERROR: only {len(cases)} eval cases loaded; need at least 4 (one per class).", file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{date.today().isoformat()}-{args.model.replace(':', '-').replace('/', '-')}-base.txt"

    # ── Warm-up ──
    cold_start_ms = 0.0
    if args.warmup_calls > 0:
        warmup_text = cases[0][2]
        if protocol == "bridge":
            t0 = time.time()
            try:
                classify_via_bridge(args.bridge_url, warmup_text)
            except Exception as e:
                print(f"ERROR: bridge unreachable for warmup: {e}", file=sys.stderr)
                sys.exit(1)
            cold_start_ms = (time.time() - t0) * 1000
        else:
            t0 = time.time()
            try:
                embed_text(args.ollama_url, args.model, warmup_text)
            except Exception as e:
                print(f"ERROR: Ollama embed failed during warmup: {e}", file=sys.stderr)
                sys.exit(1)
            cold_start_ms = (time.time() - t0) * 1000
        for _ in range(args.warmup_calls - 1):
            if protocol == "bridge":
                classify_via_bridge(args.bridge_url, warmup_text)
            else:
                embed_text(args.ollama_url, args.model, warmup_text)
        print(f"[eval] warm-up done ({args.warmup_calls} call(s)), cold_start_ms={cold_start_ms:.0f}")

    # ── Eval loop ──
    rows = []  # (path, expected, predicted, confidence, latency_ms)
    warm_latencies = []

    if protocol == "bridge":
        for path, expected, text in cases:
            tool, confidence, wall_ms = classify_via_bridge(args.bridge_url, text)
            rows.append((path, expected, tool, confidence, wall_ms))
            warm_latencies.append(wall_ms)
            mark = "OK" if tool == expected else "XX"
            print(f"  {mark} {path:42s} expected={expected:22s} got={tool:22s} ({wall_ms:.0f}ms)")
    else:  # knn
        np = _import_numpy()
        # Embed every case + measure latency for each
        embeddings = []
        for path, expected, text in cases:
            vec, wall_ms = embed_text(args.ollama_url, args.model, text)
            embeddings.append(vec)
            warm_latencies.append(wall_ms)
        X = np.stack(embeddings)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        Xn = X / np.clip(norms, 1e-12, None)
        sim = Xn @ Xn.T
        np.fill_diagonal(sim, -np.inf)
        for i, (path, expected, _text) in enumerate(cases):
            nbr = int(np.argmax(sim[i]))
            predicted = cases[nbr][1]
            confidence = float(sim[i, nbr])
            rows.append((path, expected, predicted, confidence, warm_latencies[i]))
            mark = "OK" if predicted == expected else "XX"
            print(f"  {mark} {path:42s} expected={expected:22s} got={predicted:22s} sim={confidence:.2f} ({warm_latencies[i]:.0f}ms)")

    # ── Aggregate ──
    tp = {k: 0 for k in LABELS}
    fp = {k: 0 for k in LABELS}
    fn = {k: 0 for k in LABELS}
    correct = 0
    confusion = {k: {kk: 0 for kk in LABELS} for k in LABELS}
    for _path, expected, predicted, _conf, _ms in rows:
        if predicted in LABELS:
            confusion[expected][predicted] += 1
        if predicted == expected:
            correct += 1
            tp[expected] += 1
        else:
            fp[predicted] = fp.get(predicted, 0) + 1
            fn[expected] = fn.get(expected, 0) + 1
    accuracy = correct / len(rows) if rows else 0.0
    macro_f1 = 0.0
    per_class = []
    for k in LABELS:
        p, r, f1 = f1_for_class(tp[k], fp[k], fn[k])
        per_class.append((k, p, r, f1))
        macro_f1 += f1
    macro_f1 /= len(LABELS)

    p50 = percentile(warm_latencies, 50)
    p95 = percentile(warm_latencies, 95)
    p99 = percentile(warm_latencies, 99)

    # ── Format the log file ──
    lines = []
    lines.append(f"Aegis base-model eval")
    lines.append(f"Date:     {date.today().isoformat()}")
    lines.append(f"Model:    {args.model}")
    lines.append(f"Protocol: {protocol}")
    lines.append(f"Cases:    {len(rows)}")
    lines.append(f"Warmup:   {args.warmup_calls} call(s); cold_start_ms={cold_start_ms:.0f}")
    lines.append("")
    lines.append(f"{'file':42s} {'expected':22s} {'predicted':22s} {'conf':>5s} {'ms':>7s}")
    lines.append("-" * 105)
    for path, expected, predicted, conf, ms in rows:
        mark = "OK" if predicted == expected else "XX"
        lines.append(f"{mark} {path:39s} {expected:22s} {predicted:22s} {conf:5.2f} {ms:7.0f}")
    lines.append("")
    lines.append(f"{'class':24s} {'P':>6s} {'R':>6s} {'F1':>6s}")
    lines.append("-" * 50)
    for k, p, r, f1 in per_class:
        lines.append(f"{k:24s} {p:6.2f} {r:6.2f} {f1:6.2f}")
    lines.append("")
    lines.append("Confusion matrix (rows=expected, cols=predicted):")
    header = "             " + " ".join(f"{k[:10]:>10s}" for k in LABELS)
    lines.append(header)
    for row_label in LABELS:
        cells = " ".join(f"{confusion[row_label][col]:10d}" for col in LABELS)
        lines.append(f"{row_label:12s} {cells}")
    lines.append("")
    lines.append(f"Accuracy:                {accuracy:.2%} ({correct}/{len(rows)})")
    lines.append(f"Macro F1:                {macro_f1:.3f}")
    lines.append(f"Warm latency p50:        {p50:.0f} ms")
    lines.append(f"Warm latency p95:        {p95:.0f} ms")
    lines.append(f"Warm latency p99:        {p99:.0f} ms")
    lines.append(f"Cold start (1 throwaway): {cold_start_ms:.0f} ms")
    text = "\n".join(lines) + "\n"

    with out_path.open("w") as f:
        f.write(text)
    print()
    print(text)
    print(f"[eval] wrote {out_path}")
    sys.exit(0 if accuracy > 0.0 else 1)


if __name__ == "__main__":
    main()
