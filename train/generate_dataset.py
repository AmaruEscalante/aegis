"""
Synthetic dataset generator for Aegis privacy classification.

Reads scenarios from train/prompts.py, calls Gemini per scenario,
validates the output, and appends to train/dataset.jsonl.

Each line of dataset.jsonl is a JSON object:
    {"scenario_id": "<class>:<n>", "label": "<class>", "text": "<file content>"}

Resumes from existing dataset.jsonl on rerun — skips scenarios whose
scenario_id is already present.

Usage:
    GEMINI_API_KEY=... python train/generate_dataset.py            # 50/class = 200 total
    GEMINI_API_KEY=... python train/generate_dataset.py --limit 2  # 2/class = 8 (smoke)
    GEMINI_API_KEY=... python train/generate_dataset.py --limit 4  # 4/class = 16 (validate)

Phased rollout (matches the spec):
    Stage 1 (smoke):    --limit 2  -> ~8 examples,  ~$0.01
    Stage 2 (validate): --limit 4  -> ~16 examples, ~$0.03
    Stage 3 (full):     (no limit) -> 200 examples, ~$0.20
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from google import genai

# train/ is a sibling of the repo root scripts; import the local prompts module.
# When run as `python train/generate_dataset.py` from the repo root, sys.path
# includes the script's directory (train/) so the local import works.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import SYSTEM_PROMPT, SCENARIOS  # noqa: E402


DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "dataset.jsonl"

MIN_OUTPUT_CHARS = 300
MAX_RETRIES = 2
RETRY_TEMPERATURES = [0.4, 0.7, 0.9]  # used by retry attempts in order

# Regex patterns that flag_pii outputs MUST contain at least one of, to be
# considered a valid PII-bearing file. Loose intentionally — Gemini sometimes
# produces dates as YYYY-MM-DD, sometimes MM/DD/YYYY, etc.
PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"),  # email
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                            # SSN
    re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),           # phone
    re.compile(r"\b\d{1,5}\s+\w+\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Court|Ct)\b", re.IGNORECASE),  # address
]

# Regex patterns that block_transfer outputs SHOULD contain at least one of.
# Same intent as PII_PATTERNS — looseness is intentional.
SECRET_HINT_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9]+"),                              # Stripe live key prefix
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                               # OpenAI-ish key prefix
    re.compile(r"AKIA[0-9A-Z]{16}"),                                  # AWS access key id
    re.compile(r"AIza[A-Za-z0-9_-]{20,}"),                            # GCP API key prefix
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),                              # GitHub PAT
    re.compile(r"BEGIN\s+(RSA|OPENSSH|EC|PGP)\s+PRIVATE KEY"),        # PEM private key marker
    re.compile(r"(?i)password\s*[:=]\s*\S{6,}"),                      # password=...
    re.compile(r"(?i)secret(_key|_token)?\s*[:=]\s*\S{10,}"),         # secret=, secret_key=
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*\S{10,}"),                  # api_key=, apiKey=
    re.compile(r"xox[bpoa]-[A-Za-z0-9-]{10,}"),                       # Slack token
]


def load_done_ids(path: Path) -> set:
    """Return the set of scenario_ids already present in dataset.jsonl."""
    if not path.exists():
        return set()
    done = set()
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if "scenario_id" in row:
                    done.add(row["scenario_id"])
            except json.JSONDecodeError:
                continue
    return done


def validate(label: str, text: str, scenario: str) -> tuple[bool, str]:
    """
    Return (ok, reason). reason is empty if ok=True, else explains why not.
    """
    if len(text) < MIN_OUTPUT_CHARS:
        return False, f"too short ({len(text)} < {MIN_OUTPUT_CHARS})"

    # Reject obvious instruction echo
    if scenario.lower()[:60] in text.lower():
        return False, "echoes scenario instruction"

    # Class-specific structural checks
    if label == "flag_pii":
        if not any(p.search(text) for p in PII_PATTERNS):
            return False, "flag_pii output contains no detectable PII pattern"
    elif label == "block_transfer":
        if not any(p.search(text) for p in SECRET_HINT_PATTERNS):
            return False, "block_transfer output contains no detectable secret pattern"

    return True, ""


def generate_one(client, model: str, scenario: str, temperature: float) -> str:
    """One Gemini call. Returns the raw text content."""
    full_prompt = f"{SYSTEM_PROMPT}\n\nScenario: {scenario}\n\nFile content:"
    response = client.models.generate_content(
        model=model,
        contents=full_prompt,
        config={"temperature": temperature},
    )
    return (response.text or "").strip()


def generate_with_retries(client, model: str, label: str, scenario: str) -> tuple[str, str]:
    """
    Try to generate a valid example for `scenario`. Returns (text, status).
    status is "ok" on success or the validation failure reason on giving up.
    """
    last_reason = "no attempt"
    for attempt, temp in enumerate(RETRY_TEMPERATURES[: MAX_RETRIES + 1]):
        try:
            text = generate_one(client, model, scenario, temp)
        except Exception as exc:
            last_reason = f"api error: {exc}"
            time.sleep(1.0)
            continue
        ok, reason = validate(label, text, scenario)
        if ok:
            return text, "ok"
        last_reason = reason
    return "", last_reason


def main():
    parser = argparse.ArgumentParser(description="Synthetic Aegis dataset generator")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max scenarios per class (default 50 = full 200-example set)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSONL path",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model (default {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    done = load_done_ids(args.output)
    if done:
        print(f"[generate] Resuming. {len(done)} scenarios already in {args.output}.")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    total_planned = 0
    generated = 0
    skipped = 0
    failed: list[tuple[str, str]] = []

    with args.output.open("a") as out:
        for label, scenarios in SCENARIOS.items():
            for n, scenario in enumerate(scenarios[: args.limit]):
                scenario_id = f"{label}:{n}"
                total_planned += 1

                if scenario_id in done:
                    skipped += 1
                    continue

                print(f"[{generated + skipped + len(failed) + 1:3d}/{total_planned:3d}] {scenario_id:30s} {scenario[:50]:50s} ", end="", flush=True)
                text, status = generate_with_retries(client, args.model, label, scenario)
                if status != "ok":
                    failed.append((scenario_id, status))
                    print(f"FAIL ({status})")
                    continue

                row = {"scenario_id": scenario_id, "label": label, "text": text}
                out.write(json.dumps(row) + "\n")
                out.flush()
                generated += 1
                print(f"OK ({len(text)} chars)")

    print()
    print(f"Generated: {generated}")
    print(f"Skipped (already in file): {skipped}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failures:")
        for sid, reason in failed:
            print(f"  {sid}: {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
