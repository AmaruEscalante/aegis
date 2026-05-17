"""
Aegis Classifier Benchmark — F1 + accuracy across the 4 verdict categories.

Hits the Ollama-backed Aegis bridge at http://127.0.0.1:7523/classify and
scores against a hand-labeled dataset built from samples/.

Usage:
    python benchmark.py
    python benchmark.py --bridge http://127.0.0.1:7523
"""

import argparse
import json
import sys
import time
import urllib.request

# (path, expected_tool) pairs covering all 4 categories
CASES = [
    # classify_safe
    ("samples/open_source_readme.md",      "classify_safe"),
    ("samples/marketing_copy.txt",         "classify_safe"),
    ("samples/blog_post_draft.txt",        "classify_safe"),
    # flag_pii
    ("samples/patient_records.csv",        "flag_pii"),
    ("samples/employee_directory.json",    "flag_pii"),
    ("samples/user_database.json",         "flag_pii"),
    # block_transfer
    ("samples/api_config.env",             "block_transfer"),
    ("samples/kubernetes_secrets.yaml",    "block_transfer"),
    ("samples/docker_compose_prod.yml",    "block_transfer"),
    # request_permission
    ("samples/vendor_evaluation.txt",      "request_permission"),
    ("samples/partnership_agreement.txt",  "request_permission"),
    ("samples/board_meeting_minutes.txt",  "request_permission"),
]


def post_classify(bridge_url, text):
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{bridge_url}/classify",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def f1_for_class(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def main():
    parser = argparse.ArgumentParser(description="Aegis classifier benchmark")
    parser.add_argument("--bridge", default="http://127.0.0.1:7523", help="Bridge URL")
    args = parser.parse_args()

    labels = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]
    # Per-class confusion counts
    tp = {k: 0 for k in labels}
    fp = {k: 0 for k in labels}
    fn = {k: 0 for k in labels}

    rows = []
    total_ms = 0.0

    for path, expected in CASES:
        try:
            with open(path, "r", errors="replace") as f:
                content = f.read()
        except OSError as e:
            print(f"SKIP {path}: {e}")
            continue

        start = time.time()
        try:
            result = post_classify(args.bridge, content)
        except Exception as e:
            print(f"ERROR {path}: {e}")
            continue
        wall_ms = (time.time() - start) * 1000
        total_ms += wall_ms

        predicted = result.get("tool", "request_permission")
        confidence = result.get("confidence", 0.0)
        rows.append((path, expected, predicted, confidence, wall_ms))

        if predicted == expected:
            tp[expected] += 1
        else:
            fp[predicted] = fp.get(predicted, 0) + 1
            fn[expected] = fn.get(expected, 0) + 1

    # Print per-case results
    print()
    print(f"{'file':42s} {'expected':22s} {'predicted':22s} {'conf':>5s} {'ms':>6s}")
    print("-" * 100)
    correct = 0
    for path, expected, predicted, conf, ms in rows:
        mark = "OK" if predicted == expected else "XX"
        if predicted == expected:
            correct += 1
        print(f"{mark} {path:39s} {expected:22s} {predicted:22s} {conf:5.2f} {ms:6.0f}")
    print()

    # Per-class F1
    print(f"{'class':24s} {'P':>6s} {'R':>6s} {'F1':>6s}")
    print("-" * 50)
    macro_f1 = 0.0
    for k in labels:
        p, r, f1 = f1_for_class(tp[k], fp[k], fn[k])
        macro_f1 += f1
        print(f"{k:24s} {p:6.2f} {r:6.2f} {f1:6.2f}")
    macro_f1 /= len(labels)

    total = len(rows)
    acc = correct / total if total else 0.0
    print()
    print(f"Cases:       {total}")
    print(f"Accuracy:    {acc:.2%} ({correct}/{total})")
    print(f"Macro F1:    {macro_f1:.3f}")
    print(f"Avg latency: {total_ms / total if total else 0:.0f} ms")

    sys.exit(0 if acc >= 0.5 else 1)


if __name__ == "__main__":
    main()
