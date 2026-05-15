"""
EmbeddingGemma evaluation — k-NN leave-one-out CV over 12 labeled samples.

Hits Ollama's /api/embed directly (no Aegis bridge — the bridge is a /classify
service, and EmbeddingGemma is an embedding model not a generative classifier).

Protocol:
  1. Embed all 12 samples with embeddinggemma.
  2. For each sample i, find the nearest neighbor among the other 11 (cosine
     similarity), predict its label.
  3. Score: per-class precision/recall/F1, overall accuracy, average embedding
     latency.

Usage:
    uv run python eval_embeddinggemma.py
    uv run python eval_embeddinggemma.py --model embeddinggemma --k 1
"""

import argparse
import json
import sys
import time
import urllib.request

import numpy as np

# Same 12 cases as benchmark.py for direct comparison
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

OLLAMA_DEFAULT_URL = "http://127.0.0.1:11434"
MAX_INPUT_CHARS = 8000


def embed(ollama_url, model, text):
    """Call Ollama /api/embed and return a single embedding vector."""
    truncated = text[:MAX_INPUT_CHARS]
    payload = json.dumps({"model": model, "input": truncated}).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return np.array(data["embeddings"][0], dtype=np.float32)


def cosine_sim_matrix(X):
    """X is (N, D). Returns (N, N) cosine similarity matrix."""
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    X_norm = X / np.clip(norms, 1e-12, None)
    return X_norm @ X_norm.T


def f1_for_class(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def main():
    parser = argparse.ArgumentParser(description="EmbeddingGemma k-NN LOO-CV eval")
    parser.add_argument("--model", default="embeddinggemma", help="Ollama model tag")
    parser.add_argument("--ollama-url", default=OLLAMA_DEFAULT_URL)
    parser.add_argument("--k", type=int, default=1, help="k for k-NN (default 1)")
    args = parser.parse_args()

    # Load sample text
    texts = []
    labels = []
    paths = []
    for path, label in CASES:
        try:
            with open(path, "r", errors="replace") as f:
                texts.append(f.read())
            labels.append(label)
            paths.append(path)
        except OSError as e:
            print(f"SKIP {path}: {e}")
    n = len(texts)
    if n == 0:
        print("No samples loaded; aborting.")
        sys.exit(1)

    # Embed all samples
    print(f"Embedding {n} samples with {args.model} ...")
    embeddings = []
    embed_times = []
    for i, text in enumerate(texts):
        start = time.time()
        vec = embed(args.ollama_url, args.model, text)
        elapsed_ms = (time.time() - start) * 1000
        embed_times.append(elapsed_ms)
        embeddings.append(vec)
        print(f"  [{i + 1:2d}/{n}] {paths[i]:42s} dim={vec.shape[0]} ({elapsed_ms:.0f}ms)")
    X = np.stack(embeddings)

    # Cosine similarity matrix
    sim = cosine_sim_matrix(X)
    np.fill_diagonal(sim, -np.inf)  # exclude self from k-NN

    # k-NN LOO-CV
    tp = {k: 0 for k in LABELS}
    fp = {k: 0 for k in LABELS}
    fn = {k: 0 for k in LABELS}
    correct = 0
    rows = []
    for i in range(n):
        top_k_idx = np.argsort(-sim[i])[: args.k]
        top_labels = [labels[j] for j in top_k_idx]
        # majority vote (k=1 → just the neighbor)
        predicted = max(set(top_labels), key=top_labels.count)
        rows.append((paths[i], labels[i], predicted, float(sim[i, top_k_idx[0]])))
        if predicted == labels[i]:
            correct += 1
            tp[labels[i]] += 1
        else:
            fp[predicted] = fp.get(predicted, 0) + 1
            fn[labels[i]] = fn.get(labels[i], 0) + 1

    # Per-case results
    print()
    print(f"{'file':42s} {'expected':22s} {'predicted':22s} {'sim':>5s}")
    print("-" * 95)
    for path, expected, predicted, top_sim in rows:
        mark = "OK" if predicted == expected else "XX"
        print(f"{mark} {path:39s} {expected:22s} {predicted:22s} {top_sim:5.2f}")
    print()

    # Per-class P/R/F1
    print(f"{'class':24s} {'P':>6s} {'R':>6s} {'F1':>6s}")
    print("-" * 50)
    macro_f1 = 0.0
    for k in LABELS:
        p, r, f1 = f1_for_class(tp[k], fp[k], fn[k])
        macro_f1 += f1
        print(f"{k:24s} {p:6.2f} {r:6.2f} {f1:6.2f}")
    macro_f1 /= len(LABELS)

    acc = correct / n
    print()
    print(f"Cases:               {n}")
    print(f"Accuracy:            {acc:.2%} ({correct}/{n})")
    print(f"Macro F1:            {macro_f1:.3f}")
    print(f"Avg embed latency:   {sum(embed_times) / n:.0f} ms")
    print(f"k-NN k:              {args.k}")

    sys.exit(0 if acc >= 0.5 else 1)


if __name__ == "__main__":
    main()
