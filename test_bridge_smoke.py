"""
End-to-end smoke test for the Ollama-backed Aegis bridge.

Starts no server itself — assumes `python aegis_bridge.py` is already running
on http://127.0.0.1:7523 and Ollama has `gemma4:e2b` pulled.

Exercises all 4 verdict categories against the sample files. Exits 0 on
success, 1 on any classification mismatch or transport error.
"""

import json
import sys
import time
import urllib.error
import urllib.request

BRIDGE_URL = "http://127.0.0.1:7523"

# Sample file → expected verdict (the tool name returned by /classify)
CASES = [
    ("samples/open_source_readme.md",   "classify_safe"),
    ("samples/marketing_copy.txt",      "classify_safe"),
    ("samples/patient_records.csv",     "flag_pii"),
    ("samples/employee_directory.json", "flag_pii"),
    ("samples/api_config.env",          "block_transfer"),
    ("samples/kubernetes_secrets.yaml", "block_transfer"),
    ("samples/vendor_evaluation.txt",   "request_permission"),
    ("samples/partnership_agreement.txt", "request_permission"),
]


def post_classify(text):
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{BRIDGE_URL}/classify",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def get_health():
    with urllib.request.urlopen(f"{BRIDGE_URL}/health", timeout=3) as resp:
        return json.loads(resp.read())


def main():
    try:
        health = get_health()
    except urllib.error.URLError as e:
        print(f"FAIL: bridge unreachable at {BRIDGE_URL}: {e}")
        print("Start it with: python aegis_bridge.py")
        sys.exit(1)

    print(f"Bridge health: {health}")
    assert health.get("status") == "ok", f"bridge not ok: {health}"

    failures = 0
    for path, expected_tool in CASES:
        try:
            with open(path, "r", errors="replace") as f:
                content = f.read()
        except OSError as e:
            print(f"SKIP {path}: {e}")
            continue

        start = time.time()
        result = post_classify(content)
        wall_ms = (time.time() - start) * 1000

        actual_tool = result.get("tool")
        confidence = result.get("confidence", 0)
        status = "OK  " if actual_tool == expected_tool else "FAIL"
        if actual_tool != expected_tool:
            failures += 1
        print(
            f"  [{status}] {path:42s} expected={expected_tool:20s} "
            f"got={actual_tool:20s} conf={confidence:.2f} ({wall_ms:.0f}ms)"
        )

    if failures:
        print(f"\n{failures} failure(s) out of {len(CASES)} cases")
        sys.exit(1)

    print(f"\nAll {len(CASES)} cases passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
