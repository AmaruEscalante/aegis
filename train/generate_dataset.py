"""
Synthetic dataset generator for Aegis privacy classification.

Reads scenarios from train/prompts.py, calls a local Ollama model per
scenario, validates the output, and appends to train/dataset.jsonl.

Each line of dataset.jsonl is a JSON object:
    {"scenario_id": "<class>:<n>", "label": "<class>", "text": "<file content>"}

Resumes from existing dataset.jsonl on rerun — skips scenarios whose
scenario_id is already present.

Usage:
    python train/generate_dataset.py                       # 50/class = 200 total, gemma4:e2b
    python train/generate_dataset.py --limit 2             # 2/class = 8 (smoke)
    python train/generate_dataset.py --limit 4             # 4/class = 16 (validate)
    python train/generate_dataset.py --model gemma4:31b    # higher quality, ~10x slower

Phased rollout (matches the spec):
    Stage 1 (smoke):    --limit 2  -> ~8 examples
    Stage 2 (validate): --limit 4  -> ~16 examples
    Stage 3 (full):     (no limit) -> 200 examples
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# train/ is a sibling of the repo root scripts; import the local prompts module.
# When run as `python train/generate_dataset.py` from the repo root, sys.path
# includes the script's directory (train/) so the local import works.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import SYSTEM_PROMPT, SCENARIOS  # noqa: E402

import re  # noqa: E402


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma4:e2b"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "dataset.jsonl"
OLLAMA_TIMEOUT_SECONDS = 180

MIN_OUTPUT_CHARS = 300
MAX_RETRIES = 2
RETRY_TEMPERATURES = [0.4, 0.7, 0.9]  # used by retry attempts in order

# Regex patterns that flag_pii outputs MUST contain at least one of, to be
# considered a valid PII-bearing file. Loose intentionally — Gemma sometimes
# produces dates as YYYY-MM-DD, sometimes MM/DD/YYYY, etc.
PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"),  # email
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                            # SSN
    re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),           # phone
    re.compile(
        r"\b\d{1,5}\s+(?:[NSEW]{1,2}\s+)?(?:\w+\s+){1,4}"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Court|Ct|Way|Boulevard|Blvd|Plaza|Place|Pl)\b",
        re.IGNORECASE,
    ),  # address (handles directionals + multi-word names)
]

# Regex patterns that block_transfer outputs SHOULD contain at least one of.
SECRET_HINT_PATTERNS = [
    # Specific provider token prefixes (high specificity)
    re.compile(r"sk_live_[A-Za-z0-9]+"),                                       # Stripe live key
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),                                      # OpenAI/Anthropic-style key
    re.compile(r"rk_live_[A-Za-z0-9]+"),                                       # Stripe restricted key
    re.compile(r"whsec_[A-Za-z0-9]+"),                                         # Stripe webhook secret
    re.compile(r"AKIA[0-9A-Z]{16}"),                                           # AWS access key id
    re.compile(r"ASIA[0-9A-Z]{16}"),                                           # AWS STS temporary key
    re.compile(r"AIza[A-Za-z0-9_-]{20,}"),                                     # GCP API key prefix
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),                                       # GitHub PAT
    re.compile(r"glpat-[A-Za-z0-9_-]{10,}"),                                   # GitLab PAT
    re.compile(r"GOCSPX-[A-Za-z0-9_-]{10,}"),                                  # Google OAuth client secret
    re.compile(r"xox[bpoa]-[A-Za-z0-9-]{10,}"),                                # Slack bot/user/admin token
    re.compile(r"xapp-[A-Za-z0-9-]{10,}"),                                     # Slack app token
    re.compile(r"npm_[A-Za-z0-9]{30,}"),                                       # npm auth token
    re.compile(r"pypi-[A-Za-z0-9_-]{30,}"),                                    # PyPI token
    re.compile(r"DO00[A-Z0-9]{16,}"),                                          # DigitalOcean Spaces key
    re.compile(r"WAS4[A-Z0-9]{16,}"),                                          # Wasabi access key
    re.compile(r"K004[A-Za-z0-9]{20,}"),                                       # Backblaze B2 app key
    re.compile(r"SG\.[A-Za-z0-9_.-]{20,}\.[A-Za-z0-9_.-]{20,}"),               # SendGrid full key
    re.compile(r"\bs\.[A-Za-z0-9]{20,}"),                                      # HashiCorp Vault token

    # PEM blocks (any private key)
    re.compile(r"-----BEGIN[^-]*PRIVATE KEY-----"),
    re.compile(r"-----BEGIN PGP PRIVATE KEY BLOCK-----"),

    # Generic secret-style assignments — no word boundaries (handles UPPER_PASSWORD), permissive separators (handles JSON colons and YAML)
    re.compile(r"(?i)password[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._!@#$%^&*-]{6,}"),
    re.compile(r"(?i)passphrase[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._!@#$%^&*-]{6,}"),
    re.compile(r"(?i)secret[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{8,}"),
    re.compile(r"(?i)api[_-]?key[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{8,}"),
    re.compile(r"(?i)api[_-]?token[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{10,}"),
    re.compile(r"(?i)auth[_-]?token[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{10,}"),
    re.compile(r"(?i)bot[_-]?token[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._:-]{10,}"),
    re.compile(r"(?i)client[_-]?secret[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{8,}"),
    re.compile(r"(?i)access[_-]?key[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{8,}"),
    re.compile(r"(?i)access[_-]?token[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{10,}"),
    re.compile(r"(?i)refresh[_-]?token[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{10,}"),
    re.compile(r"(?i)signing[_-]?key[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{8,}"),
    re.compile(r"(?i)private[_-]?key[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{8,}"),
    re.compile(r"(?i)encryption[_-]?key[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{8,}"),
    re.compile(r"(?i)webhook[_-]?(?:secret|token)[\s\"'_:=]+[\"']?[A-Za-z0-9+/=._-]{8,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_.-]{20,}"),
    re.compile(r"\"auth\"\s*:\s*\"[A-Za-z0-9+/=]{20,}\""),  # Docker config.json
    re.compile(r"\bcsv\s*header.*password", re.IGNORECASE),  # CSV header signal

    # URI with embedded user:password@host
    re.compile(r"[a-z]+://[^:\s/]+:[^@\s/]{4,}@[a-zA-Z0-9.-]+"),

    # Stand-alone long random strings (64+ hex chars, or 80+ base64 chars with no spaces) — pure key files
    re.compile(r"^[A-Fa-f0-9]{32,}$", re.MULTILINE),
    re.compile(r"^[A-Za-z0-9+/=]{80,}$", re.MULTILINE),
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


def ollama_chat(ollama_url: str, model: str, scenario: str, temperature: float) -> str:
    """One Ollama /api/chat call. Returns the raw generated text content."""
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Scenario: {scenario}\n\nFile content:"},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS) as resp:
        data = json.loads(resp.read())
    return (data.get("message", {}).get("content") or "").strip()


def generate_with_retries(ollama_url: str, model: str, label: str, scenario: str) -> tuple[str, str]:
    """
    Try to generate a valid example for `scenario`. Returns (text, status).
    status is "ok" on success or the validation failure reason on giving up.
    """
    last_reason = "no attempt"
    for attempt, temp in enumerate(RETRY_TEMPERATURES[: MAX_RETRIES + 1]):
        try:
            text = ollama_chat(ollama_url, model, scenario, temp)
        except Exception as exc:
            last_reason = f"ollama error: {exc}"
            time.sleep(1.0)
            continue
        ok, reason = validate(label, text, scenario)
        if ok:
            return text, "ok"
        last_reason = reason
    return "", last_reason


def main():
    parser = argparse.ArgumentParser(description="Synthetic Aegis dataset generator (Ollama backend)")
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
        help=f"Ollama model tag (default {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_URL,
        help=f"Ollama base URL (default {DEFAULT_OLLAMA_URL})",
    )
    args = parser.parse_args()

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
                text, status = generate_with_retries(args.ollama_url, args.model, label, scenario)
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
