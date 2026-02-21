"""
Aegis: Local Privacy Layer for Agentic AI

A local-first middleware that intercepts file requests from cloud AI agents,
classifies data sensitivity on-device using SmolLM2 + FunctionGemma,
and ensures sensitive data never leaves the machine without sanitization or
explicit user approval.

Architecture:
  SmolLM2 (summarizer) → FunctionGemma (router) → Python (executor) → Gemini (cloud)

Classification backends:
  --cactus         Use Cactus inference engine (default, fastest)
  --transformers   Use HuggingFace transformers (slower, highest accuracy)
"""

import json
import os
import re
import sys
import time
import urllib.request

from google import genai
from google.genai import types

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

# Cactus model paths
CACTUS_FUNCTIONGEMMA_PATH = "cactus/weights/aegis-merged"
SUMMARIZER_PATH = "cactus/weights/gemma-3-1b-it"

# Transformers model path (full merged model from training)
TRANSFORMERS_ADAPTER_PATH = "aegis-adapter"

# LM Studio config
LMSTUDIO_URL = "http://127.0.0.1:1234"
LMSTUDIO_MODEL = "smollm2-1.7b-instruct"

# Runtime flags (set via CLI args)
USE_LMSTUDIO = True  # Default: LM Studio (only working summarizer)
CLASSIFIER_BACKEND = "transformers"  # Default: transformers (100% accuracy)

# ANSI colors for CLI output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


# ─────────────────────────────────────────────
# Privacy Tools (defined for FunctionGemma)
# ─────────────────────────────────────────────

PRIVACY_TOOLS = [
    {
        "name": "classify_safe",
        "description": "The file content is safe to share with cloud AI. No sensitive data detected.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Brief reason why the file is safe",
                }
            },
            "required": ["reason"],
        },
    },
    {
        "name": "flag_pii",
        "description": "The file contains personally identifiable information (PII) like emails, phone numbers, social security numbers, or addresses that must be redacted before sharing.",
        "parameters": {
            "type": "object",
            "properties": {
                "types": {
                    "type": "string",
                    "description": "Comma-separated list of PII types found: email, ssn, phone, address, name",
                }
            },
            "required": ["types"],
        },
    },
    {
        "name": "block_transfer",
        "description": "The file contains secrets, API keys, passwords, database credentials, or encryption keys. It must NEVER be sent to the cloud.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why the file must be blocked from transfer",
                }
            },
            "required": ["reason"],
        },
    },
    {
        "name": "request_permission",
        "description": "The file contains ambiguous or potentially confidential content like trade secrets, internal project names, legal terms, or financial details. Need human approval before sharing.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "What is ambiguous and why human review is needed",
                }
            },
            "required": ["reason"],
        },
    },
]

# Wrapped format for cactus_complete
CACTUS_TOOLS = [{"type": "function", "function": t} for t in PRIVACY_TOOLS]

LABELS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]

SYSTEM_MSG = "You are a privacy classifier. Based on the file summary, call the correct tool."


# ─────────────────────────────────────────────
# Step 1: Summarize file locally (SmolLM2)
# ─────────────────────────────────────────────

SUMMARIZER_SYSTEM_PROMPT = (
    "You are a file security scanner. Summarize the file content in 2-3 sentences. "
    "Then list ANY potentially sensitive information you notice: "
    "personal names, email addresses, phone numbers, social security numbers, "
    "API keys, passwords, database credentials, encryption keys, "
    "confidential project names, trade secrets, financial figures, or legal terms. "
    "Be specific about what you found."
)


def _summarize_via_lmstudio(truncated):
    """Call SmolLM2 via LM Studio's OpenAI-compatible API (still local!)."""
    payload = json.dumps({
        "model": LMSTUDIO_MODEL,
        "messages": [
            {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Scan this file:\n\n{truncated}"},
        ],
        "max_tokens": 300,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{LMSTUDIO_URL}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    start = time.time()
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    elapsed_ms = (time.time() - start) * 1000

    summary = data["choices"][0]["message"]["content"]
    return summary, elapsed_ms


def _summarize_via_cactus(truncated):
    """Call Gemma-3-1B via Cactus (on-device)."""
    sys.path.insert(0, "cactus/python/src")
    from cactus import cactus_init, cactus_complete, cactus_destroy

    model = cactus_init(SUMMARIZER_PATH)

    messages = [
        {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Scan this file:\n\n{truncated}"},
    ]

    start = time.time()
    raw_str = cactus_complete(
        model,
        messages,
        max_tokens=300,
        temperature=0.3,
        stop_sequences=["<|im_end|>", "<end_of_turn>"],
    )
    elapsed_ms = (time.time() - start) * 1000
    cactus_destroy(model)

    try:
        raw = json.loads(raw_str)
        summary = raw.get("response", "") or ""
    except (json.JSONDecodeError, TypeError):
        summary = str(raw_str) if raw_str else ""

    return summary, elapsed_ms


def summarize_file(file_path):
    """Summarize a file locally using either LM Studio (SmolLM2) or Cactus (Gemma-3-1B)."""
    backend = "SmolLM2-1.7B via LM Studio" if USE_LMSTUDIO else "Gemma-3-1B via Cactus"
    print(f"\n{BLUE}{BOLD}[AEGIS] Step 1: Summarizing file locally{RESET}")
    print(f"  {DIM}Model: {backend} | File: {os.path.basename(file_path)}{RESET}")

    with open(file_path, "r", errors="replace") as f:
        content = f.read()

    max_chars = 8000
    truncated = content[:max_chars]
    if len(content) > max_chars:
        truncated += "\n[... file truncated ...]"

    if USE_LMSTUDIO:
        summary, elapsed_ms = _summarize_via_lmstudio(truncated)
    else:
        summary, elapsed_ms = _summarize_via_cactus(truncated)

    if not summary:
        summary = "Unable to summarize file."

    print(f"  {GREEN}Summary generated in {elapsed_ms:.0f}ms{RESET}")
    print(f"  {CYAN}{summary[:300]}{RESET}")

    return summary


# ─────────────────────────────────────────────
# Step 2: Classify sensitivity (FunctionGemma)
# ─────────────────────────────────────────────

def _classify_via_cactus(summary):
    """Classify using Cactus inference engine."""
    sys.path.insert(0, "cactus/python/src")
    from cactus import cactus_init, cactus_complete, cactus_destroy

    model = cactus_init(CACTUS_FUNCTIONGEMMA_PATH)

    messages = [
        {"role": "system", "content": SYSTEM_MSG},
        {"role": "user", "content": f"File summary:\n{summary}"},
    ]

    start = time.time()
    raw_str = cactus_complete(
        model, messages,
        tools=CACTUS_TOOLS,
        force_tools=True,
        max_tokens=256,
        confidence_threshold=0.0,
        stop_sequences=["<|im_end|>", "<end_of_turn>"],
    )
    elapsed_ms = (time.time() - start) * 1000
    cactus_destroy(model)

    # Parse Cactus response
    tool_name = "request_permission"
    tool_args = {"reason": "Unable to classify — requesting human review"}
    confidence = 0.0

    try:
        raw = json.loads(raw_str)
        confidence = raw.get("confidence", 0)
        function_calls = raw.get("function_calls", [])
        resp_text = raw.get("response", "") or ""

        if function_calls:
            tool_name = function_calls[0].get("name", "request_permission")
            tool_args = function_calls[0].get("arguments", {})
        elif resp_text:
            for label in LABELS:
                if f"call:{label}" in resp_text:
                    tool_name = label
                    try:
                        call_start = resp_text.index(f"call:{label}") + len(f"call:{label}")
                        if "{" in resp_text[call_start:call_start + 5]:
                            brace_start = resp_text.index("{", call_start)
                            brace_end = resp_text.index("}", brace_start)
                            args_str = resp_text[brace_start + 1:brace_end]
                            parsed_args = {}
                            for part in args_str.split(","):
                                part = part.strip()
                                if ":" in part:
                                    k, v = part.split(":", 1)
                                    parsed_args[k.strip()] = v.strip().replace("<escape>", "").strip()
                            if parsed_args:
                                tool_args = parsed_args
                    except (ValueError, IndexError):
                        tool_args = {"types": "email,phone,ssn"} if label == "flag_pii" else {"reason": f"classified as {label}"}
                    break
    except (json.JSONDecodeError, TypeError):
        raw_text = str(raw_str) if raw_str else ""
        for label in LABELS:
            if f"call:{label}" in raw_text:
                tool_name = label
                tool_args = {"types": "email,phone,ssn"} if label == "flag_pii" else {"reason": f"classified as {label}"}
                break

    return tool_name, tool_args, confidence, elapsed_ms


# Lazy-loaded transformers model
_tf_model = None
_tf_tokenizer = None


def _load_transformers_model():
    """Lazy-load the transformers model and tokenizer."""
    global _tf_model, _tf_tokenizer
    if _tf_model is not None:
        return _tf_model, _tf_tokenizer

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    print(f"  {DIM}Loading transformers model from {TRANSFORMERS_ADAPTER_PATH}...{RESET}")
    start = time.time()
    _tf_tokenizer = AutoTokenizer.from_pretrained(TRANSFORMERS_ADAPTER_PATH)
    _tf_model = AutoModelForCausalLM.from_pretrained(
        TRANSFORMERS_ADAPTER_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation="eager",
    )
    _tf_model.eval()
    elapsed = (time.time() - start) * 1000
    print(f"  {DIM}Model loaded in {elapsed:.0f}ms{RESET}")
    return _tf_model, _tf_tokenizer


def _classify_via_transformers(summary):
    """Classify using HuggingFace transformers (highest accuracy)."""
    import torch

    model, tokenizer = _load_transformers_model()

    messages = [
        {"role": "developer", "content": SYSTEM_MSG},
        {"role": "user", "content": f"File summary:\n{summary}"},
    ]

    inputs = tokenizer.apply_chat_template(
        messages, tools=CACTUS_TOOLS, add_generation_prompt=True,
        return_dict=True, return_tensors="pt",
    )

    start = time.time()
    with torch.no_grad():
        out = model.generate(
            **inputs.to(model.device),
            pad_token_id=tokenizer.eos_token_id,
            max_new_tokens=128,
            do_sample=False,
        )
    elapsed_ms = (time.time() - start) * 1000

    response = tokenizer.decode(
        out[0][len(inputs["input_ids"][0]):], skip_special_tokens=False
    )

    tool_name = "request_permission"
    tool_args = {"reason": "Unable to classify — requesting human review"}

    for label in LABELS:
        if f"call:{label}" in response:
            tool_name = label
            # Parse arguments from the response
            try:
                call_start = response.index(f"call:{label}") + len(f"call:{label}")
                if "{" in response[call_start:call_start + 5]:
                    brace_start = response.index("{", call_start)
                    brace_end = response.index("}", brace_start)
                    args_str = response[brace_start + 1:brace_end]
                    parsed_args = {}
                    for part in args_str.split(","):
                        part = part.strip()
                        if ":" in part:
                            k, v = part.split(":", 1)
                            parsed_args[k.strip()] = v.strip().replace("<escape>", "").strip()
                    if parsed_args:
                        tool_args = parsed_args
            except (ValueError, IndexError):
                tool_args = {"types": "email,phone,ssn"} if label == "flag_pii" else {"reason": f"classified as {label}"}
            break

    return tool_name, tool_args, 1.0, elapsed_ms


def classify_sensitivity(summary):
    """Use fine-tuned FunctionGemma to classify sensitivity."""
    print(f"\n{BLUE}{BOLD}[AEGIS] Step 2: Classifying sensitivity{RESET}")

    if CLASSIFIER_BACKEND == "transformers":
        backend_label = f"FunctionGemma via transformers | {TRANSFORMERS_ADAPTER_PATH}"
    else:
        backend_label = f"FunctionGemma via Cactus | {CACTUS_FUNCTIONGEMMA_PATH}"
    print(f"  {DIM}Model: {backend_label}{RESET}")

    if CLASSIFIER_BACKEND == "transformers":
        tool_name, tool_args, confidence, elapsed_ms = _classify_via_transformers(summary)
    else:
        tool_name, tool_args, confidence, elapsed_ms = _classify_via_cactus(summary)

    color_map = {"classify_safe": GREEN, "flag_pii": YELLOW, "block_transfer": RED, "request_permission": CYAN}
    label_map = {"classify_safe": "SAFE", "flag_pii": "SANITIZE", "block_transfer": "BLOCKED", "request_permission": "ESCALATE"}
    color = color_map.get(tool_name, RESET)
    label_str = label_map.get(tool_name, "UNKNOWN")

    print(f"  Tool: {BOLD}{tool_name}{RESET}({json.dumps(tool_args)})")
    print(f"  Confidence: {confidence:.2f} | Decision: {color}{BOLD}{label_str}{RESET}")
    print(f"  {DIM}Time: {elapsed_ms:.0f}ms{RESET}")

    return {"tool": tool_name, "arguments": tool_args, "confidence": confidence, "time_ms": elapsed_ms}


# ─────────────────────────────────────────────
# Step 3: Execute action (Python — deterministic)
# ─────────────────────────────────────────────

# Regex patterns for PII redaction
PII_PATTERNS = {
    "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
    "email": (r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL_REDACTED]"),
    "phone": (r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE_REDACTED]"),
    "api_key": (
        r"(?:sk|pk|api|key|token|secret)[-_]?\w{16,}",
        "[API_KEY_REDACTED]",
    ),
    "password": (
        r"(?<=[:=])\s*\S{8,}(?=\s|$)",
        " [PASSWORD_REDACTED]",
    ),
}


def redact_pii(content, pii_types_str="email,ssn,phone"):
    """Redact PII from content using regex patterns."""
    pii_types = [t.strip().lower() for t in pii_types_str.split(",")]
    redacted = content
    counts = {}

    for pii_type in pii_types:
        if pii_type in PII_PATTERNS:
            pattern, replacement = PII_PATTERNS[pii_type]
            matches = re.findall(pattern, redacted)
            if matches:
                counts[pii_type] = len(matches)
                redacted = re.sub(pattern, replacement, redacted)

    return redacted, counts


def execute_action(classification, file_content, file_path):
    """Execute the privacy action determined by FunctionGemma."""
    tool = classification["tool"]
    args = classification["arguments"]

    print(f"\n{BLUE}{BOLD}[AEGIS] Step 3: Executing action{RESET}")

    if tool == "classify_safe":
        print(f"  {GREEN}File is SAFE. Passing through unchanged.{RESET}")
        return {
            "action": "safe",
            "content": file_content,
            "message": f"File cleared: {args.get('reason', 'no sensitive data')}",
        }

    elif tool == "flag_pii":
        pii_types = args.get("types", "email,ssn,phone")
        print(f"  {YELLOW}Redacting PII locally: {pii_types}{RESET}")
        redacted, counts = redact_pii(file_content, pii_types)
        total = sum(counts.values())
        for pii_type, count in counts.items():
            print(f"    Replaced {count}x {pii_type}")
        print(f"  {GREEN}Total: {total} items redacted. Sanitized file ready.{RESET}")
        return {
            "action": "sanitized",
            "content": redacted,
            "redaction_counts": counts,
            "message": f"Redacted {total} PII items",
        }

    elif tool == "block_transfer":
        reason = args.get("reason", "contains secrets")
        print(f"  {RED}{BOLD}BLOCKED: {reason}{RESET}")
        print(f"  {RED}This file will NOT be sent to the cloud.{RESET}")
        return {
            "action": "blocked",
            "content": None,
            "message": f"Transfer blocked: {reason}",
        }

    elif tool == "request_permission":
        reason = args.get("reason", "ambiguous content")
        print(f"  {CYAN}Ambiguous content detected: {reason}{RESET}")
        print(f"  {CYAN}Escalating to Gemini for recommendation...{RESET}")
        return {
            "action": "escalate",
            "content": file_content,
            "reason": reason,
            "message": f"Requires review: {reason}",
        }


# ─────────────────────────────────────────────
# Step 4: Cloud escalation (Gemini)
# ─────────────────────────────────────────────

def escalate_to_gemini(summary, reason):
    """Send the SUMMARY (not raw file) to Gemini for a sensitivity recommendation."""
    print(f"\n{BLUE}{BOLD}[AEGIS] Step 4: Escalating to Gemini (summary only){RESET}")
    print(f"  {DIM}Sending file summary to cloud for classification...{RESET}")
    print(f"  {DIM}Raw file stays LOCAL — only the summary leaves the device.{RESET}")

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    start = time.time()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            f"You are a data privacy expert. A local AI flagged a file as potentially sensitive.\n\n"
            f"Reason for escalation: {reason}\n\n"
            f"File summary:\n{summary}\n\n"
            f"Based on this summary, recommend ONE action:\n"
            f"1. SAFE - the content is not sensitive, share as-is\n"
            f"2. REDACT - specific items should be masked before sharing\n"
            f"3. BLOCK - the file contains confidential information and should not be shared\n\n"
            f"Respond with your recommendation and a brief explanation."
        ),
    )
    elapsed_ms = (time.time() - start) * 1000

    recommendation = response.text if response.text else "Unable to get recommendation"
    print(f"  {GREEN}Gemini responded in {elapsed_ms:.0f}ms{RESET}")
    print(f"  {CYAN}Recommendation: {recommendation[:300]}{RESET}")

    return recommendation


def prompt_user(recommendation):
    """Ask the user what to do based on Gemini's recommendation."""
    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{YELLOW}{BOLD}  USER DECISION REQUIRED{RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")
    print(f"\n  Gemini's recommendation: {recommendation[:200]}\n")
    print(f"  {BOLD}[1]{RESET} Share file as-is")
    print(f"  {BOLD}[2]{RESET} Redact sensitive items, then share")
    print(f"  {BOLD}[3]{RESET} Block — do not share this file\n")

    choice = input(f"  {BOLD}Your choice (1/2/3): {RESET}").strip()

    if choice == "1":
        return "safe"
    elif choice == "2":
        return "redact"
    else:
        return "block"


# ─────────────────────────────────────────────
# Step 5: Cloud task execution (Gemini)
# ─────────────────────────────────────────────

def execute_cloud_task(user_query, content):
    """Send the (sanitized) content to Gemini to perform the user's actual task."""
    print(f"\n{BLUE}{BOLD}[AEGIS] Final: Executing task on cloud{RESET}")
    print(f"  {DIM}Sending sanitized content to Gemini...{RESET}")

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    start = time.time()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{user_query}\n\nFile content:\n{content[:6000]}",
    )
    elapsed_ms = (time.time() - start) * 1000

    result = response.text if response.text else "No response from Gemini"
    print(f"  {GREEN}Task completed in {elapsed_ms:.0f}ms{RESET}")

    return result


# ─────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────

def process_file(user_query, file_path):
    """Full Aegis pipeline: summarize → classify → execute → cloud task."""
    print(f"\n{'=' * 60}")
    print(f"{BOLD}{BLUE}  AEGIS — Local Privacy Layer for Agentic AI{RESET}")
    print(f"{'=' * 60}")
    print(f"  Query: {user_query}")
    print(f"  File:  {file_path}")
    print(f"  Backend: {CLASSIFIER_BACKEND}")
    print(f"{'=' * 60}")

    # Read the file
    with open(file_path, "r", errors="replace") as f:
        file_content = f.read()

    pipeline_start = time.time()

    # Step 1: Summarize locally
    summary = summarize_file(file_path)

    # Step 2: Classify sensitivity
    classification = classify_sensitivity(summary)

    # Step 3: Execute action
    result = execute_action(classification, file_content, file_path)

    # Step 4: Handle based on action
    if result["action"] == "blocked":
        total_ms = (time.time() - pipeline_start) * 1000
        print(f"\n{RED}{'=' * 60}{RESET}")
        print(f"{RED}{BOLD}  FILE BLOCKED — Nothing sent to cloud{RESET}")
        print(f"{RED}  Reason: {result['message']}{RESET}")
        print(f"{RED}  Total pipeline time: {total_ms:.0f}ms{RESET}")
        print(f"{RED}{'=' * 60}{RESET}")
        return

    if result["action"] == "escalate":
        recommendation = escalate_to_gemini(summary, result["reason"])
        user_choice = prompt_user(recommendation)

        if user_choice == "block":
            print(f"\n{RED}{BOLD}  User chose to BLOCK. Nothing sent.{RESET}")
            return
        elif user_choice == "redact":
            print(f"\n{YELLOW}  User chose to REDACT. Running redaction...{RESET}")
            redacted, counts = redact_pii(file_content, "email,ssn,phone,api_key")
            for pii_type, count in counts.items():
                print(f"    Replaced {count}x {pii_type}")
            result["content"] = redacted
        # else: safe — use original content

    # Step 5: Execute the actual user task on cloud
    cloud_result = execute_cloud_task(user_query, result["content"])

    total_ms = (time.time() - pipeline_start) * 1000

    print(f"\n{'=' * 60}")
    print(f"{GREEN}{BOLD}  TASK COMPLETE{RESET}")
    print(f"{'=' * 60}")
    print(f"  {DIM}Total pipeline time: {total_ms:.0f}ms{RESET}")
    print(f"  {DIM}Privacy status: {result['message']}{RESET}")
    print(f"\n{BOLD}Result:{RESET}\n")
    print(cloud_result[:2000])
    print()


# ─────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Parse flags
    flags = {"--lmstudio", "--cactus-summarizer", "--transformers", "--cactus"}
    args = [a for a in sys.argv[1:] if a not in flags]

    # Summarizer: LM Studio by default, --cactus-summarizer to use Cactus
    if "--cactus-summarizer" in sys.argv:
        USE_LMSTUDIO = False
        print(f"{CYAN}Summarizer: Gemma-3-1B via Cactus{RESET}")
    else:
        print(f"{CYAN}Summarizer: SmolLM2-1.7B via LM Studio ({LMSTUDIO_URL}){RESET}")

    # Classifier: transformers by default, --cactus to use Cactus
    if "--cactus" in sys.argv:
        CLASSIFIER_BACKEND = "cactus"
        print(f"{CYAN}Classifier: FunctionGemma via Cactus ({CACTUS_FUNCTIONGEMMA_PATH}){RESET}")
    else:
        print(f"{CYAN}Classifier: FunctionGemma via transformers ({TRANSFORMERS_ADAPTER_PATH}){RESET}")

    if len(args) < 2:
        print(f"\nUsage: python aegis.py [options] <query> <file_path>")
        print(f"")
        print(f"Options:")
        print(f"  --cactus              Use Cactus for FunctionGemma classification (experimental)")
        print(f"  --cactus-summarizer   Use Cactus Gemma-3-1B for summarization instead of LM Studio")
        print(f"")
        print(f"Examples:")
        print(f'  python aegis.py "Summarize this file" samples/marketing_copy.txt')
        print(f'  python aegis.py "Fix the bugs" samples/user_database.json')
        print(f'  python aegis.py --cactus "Review this config" samples/api_config.env')
        sys.exit(1)

    query = args[0]
    fpath = args[1]

    if not os.path.exists(fpath):
        print(f"{RED}Error: File not found: {fpath}{RESET}")
        sys.exit(1)

    if not os.environ.get("GEMINI_API_KEY"):
        print(f"{YELLOW}Warning: GEMINI_API_KEY not set. Cloud features will fail.{RESET}")

    process_file(query, fpath)
