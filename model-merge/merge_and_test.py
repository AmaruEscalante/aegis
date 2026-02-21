"""
Test fine-tuned FunctionGemma vs base model, then convert to Cactus format.

The aegis-adapter/ directory contains a FULL merged model (not LoRA deltas),
so no merge step is needed — just test and convert.

Compares:
  1. Base model (google/functiongemma-270m-it) — no fine-tuning
  2. Fine-tuned model (aegis-adapter/) — already merged by Unsloth

Then converts the fine-tuned model to Cactus binary format using FP16
(no quantization) to preserve the small model's learned behavior.

Usage:
    uv run python model-merge/merge_and_test.py                         # test only
    uv run python model-merge/merge_and_test.py --convert-cactus        # test + convert for Cactus
    uv run python model-merge/merge_and_test.py --convert-cactus --precision FP16
    uv run python model-merge/merge_and_test.py --skip-base             # skip base model test
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# ── Paths ───────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

BASE_MODEL_ID = "google/functiongemma-270m-it"
FINETUNED_PATH = PROJECT_ROOT / "aegis-adapter"
CACTUS_OUTPUT = PROJECT_ROOT / "cactus" / "weights" / "aegis-merged"

# Add cactus python src to path for converter imports
sys.path.insert(0, str(PROJECT_ROOT / "cactus" / "python" / "src"))

# ── Privacy tools (same as aegis.py) ────────────────────────────────────────

TOOLS = [
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

# ── Test cases ──────────────────────────────────────────────────────────────

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

SYSTEM_MSG = "You are a privacy classifier. Based on the file summary, call the correct tool."
LABELS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]


# ── Inference helper ────────────────────────────────────────────────────────

def run_inference(model, tokenizer, summary):
    """Run inference and return (predicted_tool, raw_response, time_ms)."""
    messages = [
        {"role": "developer", "content": SYSTEM_MSG},
        {"role": "user", "content": f"File summary:\n{summary}"},
    ]

    inputs = tokenizer.apply_chat_template(
        messages, tools=TOOLS, add_generation_prompt=True,
        return_dict=True, return_tensors="pt",
    )

    start = time.time()
    with torch.no_grad():
        out = model.generate(
            **inputs.to(model.device),
            pad_token_id=tokenizer.eos_token_id,
            max_new_tokens=128, do_sample=False,
        )
    elapsed_ms = (time.time() - start) * 1000

    response = tokenizer.decode(out[0][len(inputs["input_ids"][0]):], skip_special_tokens=False)

    predicted = "none"
    for tool in LABELS:
        if f"call:{tool}" in response:
            predicted = tool
            break

    return predicted, response.strip(), elapsed_ms


def run_test_suite(model, tokenizer, model_name):
    """Run all test cases and print results."""
    print(f"\n{'=' * 70}")
    print(f"  {model_name}")
    print(f"{'=' * 70}")

    correct = 0
    for tc in TEST_CASES:
        predicted, response, ms = run_inference(model, tokenizer, tc["summary"])
        ok = predicted == tc["expected"]
        if ok:
            correct += 1
        status = "\033[92mOK\033[0m" if ok else "\033[91mFAIL\033[0m"
        print(f"  [{status}] {tc['label']:>15} | expected={tc['expected']:>20} | got={predicted:>20} | {ms:.0f}ms")
        if not ok:
            resp_short = response[:120].replace("\n", " ")
            print(f"       Response: {resp_short}")

    accuracy = correct / len(TEST_CASES) * 100
    print(f"\n  Accuracy: {correct}/{len(TEST_CASES)} ({accuracy:.0f}%)")
    return correct


# ── Cactus conversion ──────────────────────────────────────────────────────

def convert_to_cactus(model_path, output_path, precision="FP16"):
    """Convert a HuggingFace model to Cactus binary format using `cactus convert` CLI."""
    import subprocess

    print(f"\n\033[1mConverting to Cactus format ({precision})...\033[0m")
    print(f"  Input:  {model_path}")
    print(f"  Output: {output_path}")

    # cactus CLI is installed in the cactus venv
    cactus_bin = str(PROJECT_ROOT / "cactus" / "venv" / "bin" / "cactus")
    cmd = [cactus_bin, "convert", str(model_path), str(output_path), "--precision", precision]
    print(f"  Running: {' '.join(cmd)}")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"\n  \033[91mCactus conversion failed (exit code {result.returncode})\033[0m")
        return False

    # Verify output
    output_path = Path(output_path)
    weight_files = list(output_path.glob("*.weights"))
    config_path = output_path / "config.txt"

    print(f"\n  \033[92mCactus conversion complete!\033[0m")
    print(f"  Weight files: {len(weight_files)}")
    print(f"  Config: {config_path}")

    if config_path.exists():
        print(f"\n  Config contents:")
        with open(config_path) as f:
            for line in f:
                print(f"    {line.rstrip()}")

    return True


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test and convert fine-tuned FunctionGemma")
    parser.add_argument("--convert-cactus", action="store_true", help="Convert to Cactus format")
    parser.add_argument("--skip-base", action="store_true", help="Skip base model test")
    parser.add_argument("--precision", default="FP16", choices=["INT4", "INT8", "FP16"],
                        help="Cactus conversion precision (default: FP16)")
    args = parser.parse_args()

    print("=" * 70)
    print("  FunctionGemma Test & Convert")
    print("=" * 70)
    print(f"  Base model:     {BASE_MODEL_ID}")
    print(f"  Fine-tuned:     {FINETUNED_PATH}")
    print(f"  Test cases:     {len(TEST_CASES)}")
    print(f"  Note: aegis-adapter/ is a FULL model (not LoRA). No merge needed.")

    # ── 1. Test base model (optional) ───────────────────────────────────
    if not args.skip_base:
        print(f"\n\033[1mLoading base model: {BASE_MODEL_ID}\033[0m")
        base_tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID, torch_dtype=torch.bfloat16,
            device_map="auto", attn_implementation="eager",
        )
        base_model.eval()
        base_correct = run_test_suite(base_model, base_tokenizer, "BASE MODEL (no fine-tuning)")
        del base_model
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    else:
        base_correct = -1

    # ── 2. Test fine-tuned model ────────────────────────────────────────
    print(f"\n\033[1mLoading fine-tuned model: {FINETUNED_PATH}\033[0m")
    ft_tokenizer = AutoTokenizer.from_pretrained(str(FINETUNED_PATH))
    ft_model = AutoModelForCausalLM.from_pretrained(
        str(FINETUNED_PATH), torch_dtype=torch.bfloat16,
        device_map="auto", attn_implementation="eager",
    )
    ft_model.eval()
    ft_correct = run_test_suite(ft_model, ft_tokenizer, "FINE-TUNED MODEL (aegis-adapter)")

    del ft_model
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    # ── 3. Comparison ───────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"  COMPARISON")
    print(f"{'=' * 70}")
    if not args.skip_base:
        print(f"  Base model:       {base_correct}/{len(TEST_CASES)} ({base_correct/len(TEST_CASES)*100:.0f}%)")
    print(f"  Fine-tuned:       {ft_correct}/{len(TEST_CASES)} ({ft_correct/len(TEST_CASES)*100:.0f}%)")

    if not args.skip_base:
        improvement = ft_correct - base_correct
        print(f"  Improvement:      +{improvement} correct ({improvement/len(TEST_CASES)*100:.0f}%)")

    # ── 4. Convert for Cactus ───────────────────────────────────────────
    if args.convert_cactus:
        success = convert_to_cactus(FINETUNED_PATH, CACTUS_OUTPUT, args.precision)
        if success:
            print(f"\n  \033[92mReady! Update aegis.py:\033[0m")
            print(f"  FUNCTIONGEMMA_PATH = 'cactus/weights/aegis-merged'")

    print(f"\n{'=' * 70}")
    print(f"  Done.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
