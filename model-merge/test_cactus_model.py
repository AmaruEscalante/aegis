"""
Test the Cactus-converted FunctionGemma model using cactus_complete.
Runs the same 6 test cases from merge_and_test.py to verify
the conversion preserved the fine-tuned behavior.

Usage:
    uv run python model-merge/test_cactus_model.py
    uv run python model-merge/test_cactus_model.py --model cactus/weights/aegis-adapter   # test old INT8
    uv run python model-merge/test_cactus_model.py --model cactus/weights/aegis-merged    # test new FP16
"""

import sys
import os
import json
import time
import argparse

sys.path.insert(0, "cactus/python/src")
from cactus import cactus_init, cactus_complete, cactus_destroy

# ── Config ──────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "cactus/weights/aegis-merged"

PRIVACY_TOOLS = [
    {"type": "function", "function": {
        "name": "classify_safe",
        "description": "The file content is safe to share with cloud AI. No sensitive data detected.",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
    }},
    {"type": "function", "function": {
        "name": "flag_pii",
        "description": "The file contains personally identifiable information (PII) like emails, phone numbers, social security numbers, or addresses that must be redacted before sharing.",
        "parameters": {"type": "object", "properties": {"types": {"type": "string"}}, "required": ["types"]},
    }},
    {"type": "function", "function": {
        "name": "block_transfer",
        "description": "The file contains secrets, API keys, passwords, database credentials, or encryption keys. It must NEVER be sent to the cloud.",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
    }},
    {"type": "function", "function": {
        "name": "request_permission",
        "description": "The file contains ambiguous or potentially confidential content like trade secrets, internal project names, legal terms, or financial details. Need human approval before sharing.",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
    }},
]

LABELS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]

TEST_CASES = [
    {
        "label": "SAFE",
        "expected": "classify_safe",
        "summary": "This is a public README file for an open-source Python library. It describes installation instructions, API usage examples, and benchmarks. No sensitive information found.",
    },
    {
        "label": "PII",
        "expected": "flag_pii",
        "summary": "CSV export containing 500 customer records with full names, email addresses like john.doe@gmail.com, phone numbers (415) 555-0123, and Social Security Numbers in the format 329-44-8812. Also includes home addresses.",
    },
    {
        "label": "BLOCK",
        "expected": "block_transfer",
        "summary": "Configuration file containing AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCY, database connection strings with passwords postgres://admin:secret@db:5432/main, and Stripe API keys sk_live_abc123def456 in plaintext.",
    },
    {
        "label": "ESCALATE",
        "expected": "request_permission",
        "summary": "Board meeting minutes from February 2026 discussing Q4 revenue of $847M, a potential acquisition of DataSync Labs at $120M valuation (material non-public information), executive compensation details, and the Singapore office expansion plan.",
    },
    {
        "label": "SAFE (tricky)",
        "expected": "classify_safe",
        "summary": "A blog post about AI trends in supply chain management, citing public McKinsey reports and mentioning publicly traded companies like Target and Walmart. All metrics referenced are from published annual reports. No PII detected.",
    },
    {
        "label": "BLOCK (k8s)",
        "expected": "block_transfer",
        "summary": "Kubernetes secrets YAML file with base64-encoded production credentials including STRIPE_SECRET_KEY, DATABASE_URL with admin password, Redis password, JWT signing key, and AWS access keys.",
    },
]

# ANSI
GREEN = "\033[92m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


LOG_FILE = "model-merge/cactus_test_log.json"

def classify(model, summary, log_entries):
    """Run classification and return (tool_name, raw_response, time_ms, confidence)."""
    messages = [
        {"role": "system", "content": "You are a privacy classifier. Based on the file summary, call the correct tool."},
        {"role": "user", "content": f"File summary:\n{summary}"},
    ]

    start = time.time()
    raw_str = cactus_complete(
        model, messages,
        tools=PRIVACY_TOOLS,
        force_tools=True,
        max_tokens=256,
        confidence_threshold=0.0,
        stop_sequences=["<|im_end|>", "<end_of_turn>"],
    )
    elapsed_ms = (time.time() - start) * 1000

    # Log the complete raw output
    log_entries.append({
        "summary": summary[:100] + "...",
        "raw_cactus_output": raw_str,
        "elapsed_ms": elapsed_ms,
    })

    tool_name = "none"
    confidence = 0.0
    response_text = ""

    try:
        raw = json.loads(raw_str)
        confidence = raw.get("confidence", 0)
        response_text = raw.get("response", "") or ""
        function_calls = raw.get("function_calls", [])

        if function_calls:
            tool_name = function_calls[0].get("name", "none")
        elif response_text:
            for label in LABELS:
                if f"call:{label}" in response_text:
                    tool_name = label
                    break
    except (json.JSONDecodeError, TypeError):
        raw_text = str(raw_str) if raw_str else ""
        response_text = raw_text
        for label in LABELS:
            if f"call:{label}" in raw_text:
                tool_name = label
                break

    return tool_name, response_text, elapsed_ms, confidence


def main():
    parser = argparse.ArgumentParser(description="Test Cactus-converted FunctionGemma")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Cactus model path")
    args = parser.parse_args()

    print(f"\n{'=' * 70}")
    print(f"  Cactus Model Test — {args.model}")
    print(f"{'=' * 70}")

    # Load model
    print(f"  Loading model...")
    load_start = time.time()
    model = cactus_init(args.model)
    load_ms = (time.time() - load_start) * 1000
    print(f"  Model loaded in {load_ms:.0f}ms\n")

    correct = 0
    total_inference_ms = 0
    log_entries = []

    for tc in TEST_CASES:
        tool_name, response, ms, confidence = classify(model, tc["summary"], log_entries)
        total_inference_ms += ms
        ok = tool_name == tc["expected"]
        if ok:
            correct += 1

        status = f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  [{status}] {tc['label']:>15} | expected={tc['expected']:>20} | got={tool_name:>20} | {ms:.0f}ms | conf={confidence:.2f}")
        if not ok:
            resp_short = response[:150].replace("\n", " ")
            print(f"       {DIM}Response: {resp_short}{RESET}")

    cactus_destroy(model)

    # Write full log
    with open(LOG_FILE, "w") as f:
        json.dump(log_entries, f, indent=2, ensure_ascii=False)
    print(f"\n  Full raw outputs logged to {LOG_FILE}")

    accuracy = correct / len(TEST_CASES) * 100
    avg_ms = total_inference_ms / len(TEST_CASES)

    print(f"\n{'=' * 70}")
    print(f"  Results: {correct}/{len(TEST_CASES)} ({accuracy:.0f}%)")
    print(f"  Avg inference: {avg_ms:.0f}ms")
    print(f"  Model load: {load_ms:.0f}ms")
    print(f"{'=' * 70}")

    if correct == len(TEST_CASES):
        print(f"\n  {GREEN}{BOLD}ALL TESTS PASSED — Cactus conversion preserved fine-tuning!{RESET}")
        print(f"  Update aegis.py: FUNCTIONGEMMA_PATH = '{args.model}'")
    else:
        print(f"\n  {RED}{BOLD}SOME TESTS FAILED — conversion may have degraded the model.{RESET}")
        print(f"  Try: --precision FP16 if you used INT8, or check missing_weights.txt")


if __name__ == "__main__":
    main()
