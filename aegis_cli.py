"""
Aegis CLI — Interactive end-to-end test harness for the Aegis privacy router.

Processes files through the full pipeline and shows every step visually:
  Step 1: Read file from disk
  Step 2: Classify (via bridge /classify → FunctionGemma)
  Step 3: Route decision (safe / flag_pii / block / escalate)
  Step 4: Execute action (passthrough / regex redaction / deny / escalate)

Usage:
  # Single file
  python aegis_cli.py samples/patient_records.csv

  # Multiple files
  python aegis_cli.py samples/marketing_copy.txt samples/kubernetes_secrets.yaml

  # All sample files
  python aegis_cli.py --all

  # With custom bridge URL
  python aegis_cli.py --bridge http://127.0.0.1:7523 samples/user_database.json

  # Just classification (no action execution)
  python aegis_cli.py --classify-only samples/api_config.env

Requires the bridge to be running:
  uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter
"""

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.request

# ── ANSI colors ────────────────────────────────────────────────────────────

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── Regex PII patterns (same as aegis.py) ──────────────────────────────────

PII_PATTERNS = {
    "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
    "email": (r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL_REDACTED]"),
    "phone": (r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE_REDACTED]"),
    "api_key": (r"(?:sk|pk|api|key|token|secret)[-_]?\w{16,}", "[API_KEY_REDACTED]"),
    "password": (r"(?<=[:=])\s*\S{8,}(?=\s|$)", " [PASSWORD_REDACTED]"),
    "address": (r"\d+\s[\w\s]+(?:St|Ave|Blvd|Dr|Rd|Lane|Way|Ct)\b", "[ADDRESS_REDACTED]"),
    "name": (r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b", "[NAME_REDACTED]"),
}

# Map model output PII type names → regex pattern keys.
# FunctionGemma returns types like "APIKEY", "Name", "SSN" but our regex
# patterns use snake_case keys. This normalizes any known variant.
PII_TYPE_ALIASES = {
    "apikey": "api_key",
    "api_key": "api_key",
    "api key": "api_key",
    "ssn": "ssn",
    "social security": "ssn",
    "email": "email",
    "phone": "phone",
    "telephone": "phone",
    "phone number": "phone",
    "name": "name",
    "names": "name",
    "address": "address",
    "password": "password",
    "passwords": "password",
    "credential": "password",
    "credentials": "password",
}


def normalize_pii_types(types_str):
    """Normalize model-returned PII type strings to regex pattern keys.

    Handles: "APIKEY" → "api_key", "Name" → "name", "SSN" → "ssn", etc.
    If nothing matches, fall back to running ALL patterns.
    """
    raw_types = [t.strip() for t in types_str.split(",")]
    normalized = set()
    for raw in raw_types:
        key = raw.lower().strip()
        if key in PII_TYPE_ALIASES:
            normalized.add(PII_TYPE_ALIASES[key])
        elif key in PII_PATTERNS:
            normalized.add(key)
        else:
            # Unknown type — run all patterns as safety net
            return list(PII_PATTERNS.keys())
    return list(normalized) if normalized else list(PII_PATTERNS.keys())


# ── Bridge HTTP helpers ────────────────────────────────────────────────────

def bridge_post(bridge_url, path, body, timeout=15):
    """POST JSON to the bridge server."""
    url = f"{bridge_url}{path}"
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def bridge_health(bridge_url, timeout=3):
    """Check bridge health."""
    try:
        url = f"{bridge_url}/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return {"status": "unreachable"}


# ── Pipeline steps ─────────────────────────────────────────────────────────

def step_read_file(file_path):
    """Step 1: Read file from disk."""
    print(f"\n{BLUE}{BOLD}[AEGIS] Step 1: Reading file{RESET}")
    print(f"  {DIM}Path: {file_path}{RESET}")

    if not os.path.exists(file_path):
        print(f"  {RED}ERROR: File not found{RESET}")
        return None

    stat = os.stat(file_path)
    print(f"  {DIM}Size: {stat.st_size:,} bytes{RESET}")

    with open(file_path, "r", errors="replace") as f:
        content = f.read()

    ext = os.path.splitext(file_path)[1]
    print(f"  {DIM}Type: {ext or 'no extension'} | {len(content):,} chars{RESET}")
    print(f"  {GREEN}File loaded.{RESET}")
    return content


def step_classify(bridge_url, content):
    """Step 2: Classify via bridge (FunctionGemma)."""
    print(f"\n{BLUE}{BOLD}[AEGIS] Step 2: Classifying sensitivity (FunctionGemma){RESET}")
    print(f"  {DIM}Sending first 8000 chars to bridge /classify ...{RESET}")

    start = time.time()
    try:
        resp = bridge_post(bridge_url, "/classify", {"text": content[:8000]})
    except Exception as e:
        print(f"  {RED}ERROR: Bridge /classify failed: {e}{RESET}")
        print(f"  {YELLOW}Falling back to: flag_pii (sanitize everything){RESET}")
        return {
            "tool": "flag_pii",
            "arguments": {"types": "email,phone,ssn"},
            "confidence": 0,
            "time_ms": 0,
        }, 0

    elapsed_ms = (time.time() - start) * 1000

    tool = resp.get("tool", "flag_pii")
    args = resp.get("arguments", {})
    confidence = resp.get("confidence", 0)
    bridge_ms = resp.get("time_ms", 0)

    # Color-code by verdict
    color_map = {
        "classify_safe": GREEN,
        "flag_pii": YELLOW,
        "block_transfer": RED,
        "request_permission": CYAN,
    }
    label_map = {
        "classify_safe": "SAFE",
        "flag_pii": "SANITIZE (PII detected)",
        "block_transfer": "BLOCKED (secrets detected)",
        "request_permission": "ESCALATE (needs human review)",
    }

    color = color_map.get(tool, RESET)
    label = label_map.get(tool, f"UNKNOWN ({tool})")

    print(f"  {DIM}Tool call: {BOLD}{tool}{RESET}{DIM}({json.dumps(args)}){RESET}")
    print(f"  {DIM}Confidence: {confidence:.2f} | Time: {elapsed_ms:.0f}ms (bridge: {bridge_ms:.0f}ms){RESET}")
    print(f"  {color}{BOLD}  ╔══════════════════════════════════════╗{RESET}")
    print(f"  {color}{BOLD}  ║  VERDICT: {label:29s}║{RESET}")
    print(f"  {color}{BOLD}  ╚══════════════════════════════════════╝{RESET}")

    return resp, elapsed_ms


def step_execute(classification, content, file_path):
    """Step 3: Execute the action based on classification."""
    tool = classification.get("tool", "flag_pii")
    args = classification.get("arguments", {})

    print(f"\n{BLUE}{BOLD}[AEGIS] Step 3: Executing action{RESET}")

    if tool == "classify_safe":
        print(f"  {GREEN}Action: PASSTHROUGH — returning raw file content{RESET}")
        print(f"  {DIM}No sanitization needed. File is safe to share.{RESET}")
        # Show a preview
        preview = content[:300]
        print(f"  {DIM}─── Content preview (first 300 chars) ───{RESET}")
        for line in preview.split("\n")[:10]:
            print(f"  {line}")
        return {"action": "safe", "content": content}

    elif tool == "flag_pii":
        pii_types_str = args.get("types", "email,ssn,phone")
        pii_types = normalize_pii_types(pii_types_str)
        print(f"  {YELLOW}Action: SANITIZE — model requested: {pii_types_str}{RESET}")
        print(f"  {DIM}Normalized to regex keys: {', '.join(pii_types)}{RESET}")

        redacted = content
        total_count = 0
        for pii_type in pii_types:
            if pii_type in PII_PATTERNS:
                pattern, replacement = PII_PATTERNS[pii_type]
                matches = re.findall(pattern, redacted)
                if matches:
                    count = len(matches)
                    total_count += count
                    redacted = re.sub(pattern, replacement, redacted)
                    print(f"    {YELLOW}├─ {pii_type}: {count} items redacted{RESET}")

        if total_count == 0:
            print(f"    {DIM}(no regex matches for the specified PII types){RESET}")
        else:
            print(f"    {GREEN}└─ Total: {total_count} items redacted{RESET}")

        # Show before/after diff
        print(f"  {DIM}─── Redacted content preview (first 400 chars) ───{RESET}")
        for line in redacted[:400].split("\n")[:12]:
            # Highlight redacted tokens
            highlighted = line
            for tag in ["[SSN_REDACTED]", "[EMAIL_REDACTED]", "[PHONE_REDACTED]",
                        "[API_KEY_REDACTED]", "[PASSWORD_REDACTED]", "[ADDRESS_REDACTED]",
                        "[NAME_REDACTED]"]:
                highlighted = highlighted.replace(tag, f"{RED}{BOLD}{tag}{RESET}")
            print(f"  {highlighted}")

        return {"action": "sanitized", "content": redacted, "redaction_count": total_count}

    elif tool == "block_transfer":
        reason = args.get("reason", "contains secrets")
        print(f"  {RED}{BOLD}Action: BLOCK — file access denied{RESET}")
        print(f"  {RED}Reason: {reason}{RESET}")
        print(f"  {RED}This file will NOT be shared with any cloud service.{RESET}")
        print(f"  {DIM}The raw content stays on-device and is never transmitted.{RESET}")
        return {"action": "blocked", "content": None, "reason": reason}

    elif tool == "request_permission":
        reason = args.get("reason", "ambiguous content")
        print(f"  {CYAN}{BOLD}Action: ESCALATE — human review required{RESET}")
        print(f"  {CYAN}Reason: {reason}{RESET}")
        print(f"  {DIM}In the OpenClaw plugin, this would return a structured{RESET}")
        print(f"  {DIM}escalation message asking the agent to get user approval.{RESET}")
        print(f"")
        print(f"  {BOLD}╔══════════════════════════════════════════╗{RESET}")
        print(f"  {BOLD}║  {YELLOW}USER DECISION REQUIRED{RESET}{BOLD}                  ║{RESET}")
        print(f"  {BOLD}║  {DIM}Aegis cannot determine if this file{RESET}{BOLD}     ║{RESET}")
        print(f"  {BOLD}║  {DIM}is safe to share. Please review.{RESET}{BOLD}        ║{RESET}")
        print(f"  {BOLD}╚══════════════════════════════════════════╝{RESET}")
        return {"action": "escalate", "content": None, "reason": reason}

    else:
        print(f"  {RED}Unknown tool: {tool} — treating as flag_pii{RESET}")
        return step_execute({"tool": "flag_pii", "arguments": {"types": "email,ssn,phone"}}, content, file_path)


# ── Process a single file ──────────────────────────────────────────────────

def process_file(file_path, bridge_url, classify_only=False):
    """Run the full Aegis pipeline on a single file."""
    basename = os.path.basename(file_path)
    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{MAGENTA}{BOLD}  AEGIS PIPELINE: {basename}{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}")

    total_start = time.time()

    # Step 1: Read
    content = step_read_file(file_path)
    if content is None:
        return None

    # Step 2: Classify
    classification, classify_ms = step_classify(bridge_url, content)

    if classify_only:
        print(f"\n{DIM}  (--classify-only: skipping action execution){RESET}")
        print(f"\n{BLUE}{BOLD}[AEGIS] Pipeline complete{RESET}")
        print(f"  {DIM}Total time: {classify_ms:.0f}ms{RESET}")
        return {
            "file": basename,
            "verdict": classification.get("tool"),
            "confidence": classification.get("confidence"),
            "time_ms": classify_ms,
        }

    # Step 3: Execute action
    result = step_execute(classification, content, file_path)

    total_ms = (time.time() - total_start) * 1000

    # Summary line
    print(f"\n{BLUE}{BOLD}[AEGIS] Pipeline complete{RESET}")
    print(f"  {DIM}Total time: {classify_ms:.0f}ms{RESET}")

    return {
        "file": basename,
        "verdict": classification.get("tool"),
        "arguments": classification.get("arguments"),
        "confidence": classification.get("confidence"),
        "action": result.get("action"),
        "redaction_count": result.get("redaction_count", 0),
        "time_ms": total_ms,
    }


# ── Batch summary ──────────────────────────────────────────────────────────

def print_batch_summary(results):
    """Print a summary table after processing multiple files."""
    print(f"\n\n{BOLD}{'═' * 70}{RESET}")
    print(f"{MAGENTA}{BOLD}  BATCH SUMMARY{RESET}")
    print(f"{BOLD}{'═' * 70}{RESET}")
    print(f"  {'File':<35} {'Verdict':<22} {'Conf':>5}  {'Time':>6}")
    print(f"  {'─' * 35} {'─' * 22} {'─' * 5}  {'─' * 6}")

    verdict_colors = {
        "classify_safe": GREEN,
        "flag_pii": YELLOW,
        "block_transfer": RED,
        "request_permission": CYAN,
    }
    verdict_labels = {
        "classify_safe": "SAFE",
        "flag_pii": "SANITIZE",
        "block_transfer": "BLOCKED",
        "request_permission": "ESCALATE",
    }

    counts = {"classify_safe": 0, "flag_pii": 0, "block_transfer": 0, "request_permission": 0}

    for r in results:
        if r is None:
            continue
        verdict = r.get("verdict", "unknown")
        color = verdict_colors.get(verdict, RESET)
        label = verdict_labels.get(verdict, verdict)
        conf = r.get("confidence", 0)
        ms = r.get("time_ms", 0)
        fname = r.get("file", "?")[:34]
        counts[verdict] = counts.get(verdict, 0) + 1
        print(f"  {fname:<35} {color}{BOLD}{label:<22}{RESET} {conf:>5.2f}  {ms:>5.0f}ms")

    total = len([r for r in results if r is not None])
    print(f"\n  {BOLD}Total: {total} files{RESET}")
    print(f"    {GREEN}Safe: {counts['classify_safe']}{RESET}  "
          f"{YELLOW}Sanitize: {counts['flag_pii']}{RESET}  "
          f"{RED}Blocked: {counts['block_transfer']}{RESET}  "
          f"{CYAN}Escalate: {counts['request_permission']}{RESET}")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Aegis CLI — test the full privacy router pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python aegis_cli.py samples/patient_records.csv\n"
            "  python aegis_cli.py --all\n"
            "  python aegis_cli.py --classify-only samples/*.txt\n"
            "  python aegis_cli.py --bridge http://127.0.0.1:7523 samples/api_config.env\n"
        ),
    )
    parser.add_argument("files", nargs="*", help="File(s) to process")
    parser.add_argument("--all", action="store_true", help="Process all files in samples/")
    parser.add_argument("--bridge", default="http://127.0.0.1:7523", help="Bridge URL (default: http://127.0.0.1:7523)")
    parser.add_argument("--classify-only", action="store_true", help="Only classify, don't execute actions")

    args = parser.parse_args()

    # Resolve file list
    files = list(args.files)
    if args.all:
        samples_dir = os.path.join(os.path.dirname(__file__) or ".", "samples")
        files = sorted(glob.glob(os.path.join(samples_dir, "*")))
        if not files:
            print(f"{RED}ERROR: No files found in {samples_dir}{RESET}")
            sys.exit(1)

    if not files:
        parser.print_help()
        sys.exit(0)

    # Check bridge health
    print(f"{BOLD}Aegis CLI — Privacy Router Test Harness{RESET}")
    print(f"{DIM}Bridge: {args.bridge}{RESET}")

    health = bridge_health(args.bridge)
    if health.get("status") == "ok":
        print(f"{GREEN}Bridge: connected (backend={health.get('backend')}, model={health.get('model')}){RESET}")
    else:
        print(f"{RED}Bridge: UNREACHABLE at {args.bridge}{RESET}")
        print(f"{YELLOW}Start it with: uv run python aegis_bridge.py --backend transformers --model ./aegis-adapter{RESET}")
        sys.exit(1)

    print(f"{DIM}Files: {len(files)} to process{RESET}")

    # Process files
    results = []
    for file_path in files:
        result = process_file(file_path, args.bridge, classify_only=args.classify_only)
        results.append(result)

    # Batch summary (if multiple files)
    if len(files) > 1:
        print_batch_summary(results)

    print()


if __name__ == "__main__":
    main()
