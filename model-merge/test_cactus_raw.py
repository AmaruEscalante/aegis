"""
Test the Cactus-converted FunctionGemma using RAW prompt format
(matching exactly what transformers' apply_chat_template produces).

Bypasses Cactus's own tool formatting — sends the prompt as plain text.

Usage:
    uv run python model-merge/test_cactus_raw.py
    uv run python model-merge/test_cactus_raw.py --model cactus/weights/aegis-merged
"""

import sys
import os
import json
import time
import argparse

sys.path.insert(0, "cactus/python/src")
from cactus import cactus_init, cactus_complete, cactus_destroy

DEFAULT_MODEL = "cactus/weights/aegis-merged"

LABELS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]

# The EXACT tool declarations as formatted by transformers' Gemma 3 chat template
TOOL_DECLARATIONS = (
    '<start_function_declaration>declaration:classify_safe{description:<escape>The file content is safe to share with cloud AI. No sensitive data detected.<escape>,parameters:{properties:{reason:{description:<escape>Brief reason why the file is safe<escape>,type:<escape>STRING<escape>}},required:[<escape>reason<escape>],type:<escape>OBJECT<escape>}}<end_function_declaration>'
    '<start_function_declaration>declaration:flag_pii{description:<escape>The file contains personally identifiable information (PII) like emails, phone numbers, social security numbers, or addresses that must be redacted before sharing.<escape>,parameters:{properties:{types:{description:<escape>Comma-separated list of PII types found<escape>,type:<escape>STRING<escape>}},required:[<escape>types<escape>],type:<escape>OBJECT<escape>}}<end_function_declaration>'
    '<start_function_declaration>declaration:block_transfer{description:<escape>The file contains secrets, API keys, passwords, database credentials, or encryption keys. It must NEVER be sent to the cloud.<escape>,parameters:{properties:{reason:{description:<escape>Why the file must be blocked from transfer<escape>,type:<escape>STRING<escape>}},required:[<escape>reason<escape>],type:<escape>OBJECT<escape>}}<end_function_declaration>'
    '<start_function_declaration>declaration:request_permission{description:<escape>The file contains ambiguous or potentially confidential content like trade secrets, internal project names, legal terms, or financial details. Need human approval before sharing.<escape>,parameters:{properties:{reason:{description:<escape>What is ambiguous and why human review is needed<escape>,type:<escape>STRING<escape>}},required:[<escape>reason<escape>],type:<escape>OBJECT<escape>}}<end_function_declaration>'
)

SYSTEM_MSG = "You are a privacy classifier. Based on the file summary, call the correct tool."

TEST_CASES = [
    {"label": "SAFE", "expected": "classify_safe",
     "summary": "This is a public README file for an open-source Python library. It describes installation instructions, API usage examples, and benchmarks. No sensitive information found."},
    {"label": "PII", "expected": "flag_pii",
     "summary": "CSV export containing 500 customer records with full names, email addresses like john.doe@gmail.com, phone numbers (415) 555-0123, and Social Security Numbers in the format 329-44-8812. Also includes home addresses."},
    {"label": "BLOCK", "expected": "block_transfer",
     "summary": "Configuration file containing AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCY, database connection strings with passwords postgres://admin:secret@db:5432/main, and Stripe API keys sk_live_abc123def456 in plaintext."},
    {"label": "ESCALATE", "expected": "request_permission",
     "summary": "Board meeting minutes from February 2026 discussing Q4 revenue of $847M, a potential acquisition of DataSync Labs at $120M valuation (material non-public information), executive compensation details, and the Singapore office expansion plan."},
    {"label": "SAFE (tricky)", "expected": "classify_safe",
     "summary": "A blog post about AI trends in supply chain management, citing public McKinsey reports and mentioning publicly traded companies like Target and Walmart. All metrics referenced are from published annual reports. No PII detected."},
    {"label": "BLOCK (k8s)", "expected": "block_transfer",
     "summary": "Kubernetes secrets YAML file with base64-encoded production credentials including STRIPE_SECRET_KEY, DATABASE_URL with admin password, Redis password, JWT signing key, and AWS access keys."},
]

GREEN = "\033[92m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def build_raw_prompt(summary):
    """Build the exact prompt that transformers' apply_chat_template produces."""
    return (
        f"<start_of_turn>developer\n"
        f"{SYSTEM_MSG}{TOOL_DECLARATIONS}<end_of_turn>\n"
        f"<start_of_turn>user\n"
        f"File summary:\n{summary}<end_of_turn>\n"
        f"<start_of_turn>model\n"
    )


def classify(model, summary):
    """Send raw prompt to Cactus and parse the response."""
    prompt = build_raw_prompt(summary)

    # Send as a single user message containing the full formatted prompt
    # No tools, no force_tools — just raw text
    messages = [{"role": "user", "content": prompt}]

    start = time.time()
    raw_str = cactus_complete(
        model, messages,
        max_tokens=128,
        confidence_threshold=0.0,
        stop_sequences=["<end_of_turn>", "<start_of_turn>"],
    )
    elapsed_ms = (time.time() - start) * 1000

    tool_name = "none"
    confidence = 0.0
    response_text = ""

    try:
        raw = json.loads(raw_str)
        confidence = raw.get("confidence", 0)
        response_text = raw.get("response", "") or ""
    except (json.JSONDecodeError, TypeError):
        response_text = str(raw_str) if raw_str else ""

    # Extract tool call from response
    for label in LABELS:
        if f"call:{label}" in response_text:
            tool_name = label
            break

    return tool_name, response_text, elapsed_ms, confidence


def main():
    parser = argparse.ArgumentParser(description="Test Cactus model with raw prompt format")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Cactus model path")
    parser.add_argument("--verbose", action="store_true", help="Show full responses")
    args = parser.parse_args()

    print(f"\n{'=' * 70}")
    print(f"  Cactus Raw Prompt Test — {args.model}")
    print(f"{'=' * 70}")

    print(f"  Loading model...")
    load_start = time.time()
    model = cactus_init(args.model)
    load_ms = (time.time() - load_start) * 1000
    print(f"  Model loaded in {load_ms:.0f}ms")

    # Show what prompt looks like
    sample_prompt = build_raw_prompt("test")
    print(f"  Prompt format: raw text matching transformers chat template")
    print(f"  Prompt length: ~{len(build_raw_prompt(TEST_CASES[0]['summary']))} chars\n")

    correct = 0
    total_ms = 0

    for tc in TEST_CASES:
        tool_name, response, ms, confidence = classify(model, tc["summary"])
        total_ms += ms
        ok = tool_name == tc["expected"]
        if ok:
            correct += 1

        status = f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  [{status}] {tc['label']:>15} | expected={tc['expected']:>20} | got={tool_name:>20} | {ms:.0f}ms | conf={confidence:.2f}")
        if not ok or args.verbose:
            resp_short = response[:200].replace("\n", " ")
            print(f"       {DIM}Response: {resp_short}{RESET}")

    cactus_destroy(model)

    accuracy = correct / len(TEST_CASES) * 100
    avg_ms = total_ms / len(TEST_CASES)

    print(f"\n{'=' * 70}")
    print(f"  Results: {correct}/{len(TEST_CASES)} ({accuracy:.0f}%)")
    print(f"  Avg inference: {avg_ms:.0f}ms")
    print(f"{'=' * 70}")

    if correct == len(TEST_CASES):
        print(f"\n  {GREEN}{BOLD}ALL TESTS PASSED!{RESET}")
    elif correct >= 5:
        print(f"\n  {GREEN}Almost there — {correct}/6 correct.{RESET}")
    else:
        print(f"\n  {RED}Raw prompt format didn't help. Consider transformers fallback.{RESET}")


if __name__ == "__main__":
    main()
