# Aegis: Local Privacy Layer for Agentic AI

## Context

Hackathon: Google DeepMind x Cactus Compute Global Hackathon (Feb 21, 2026)
Challenge: Build an agentic system with intelligent local/cloud routing using FunctionGemma + Cactus + Gemini.

Cloud AI agents need file access to be useful, but granting blanket access leaks PII, secrets, and confidential data. Aegis is an intelligent local-first middleware that classifies data sensitivity on-device, ensuring sensitive data never leaves the machine without sanitization or explicit user approval.

## Architecture

```
User: "Analyze my Q3 report" + file
         │
         ▼
┌──────────────────────────────────────────┐
│  LOCAL LAYER (nothing leaves the device) │
│                                          │
│  Step 1: SmolLM2-1.7B summarizes file    │
│          → ~200 token summary with       │
│            sensitivity notes             │
│                                          │
│  Step 2: FunctionGemma reads summary     │
│          → calls one of 4 privacy tools  │
│                                          │
│  Step 3: Python executes the tool call   │
│          (deterministic, no LLM)         │
└──────────┬───────────────────────────────┘
           │
     ┌─────┴──────────────────────────┐
     │ Tool called?                   │
     ├─ classify_safe()               │→ Pass raw file to Gemini
     ├─ flag_pii(types=[...])         │→ Regex redacts locally, send cleaned file to Gemini
     ├─ block_transfer(reason)        │→ Denied. Nothing sent.
     └─ request_permission(reason)    │→ Send SUMMARY to Gemini for judgment,
                                      │  present recommendation to user,
                                      │  user confirms → then send file/redacted/block
                                      │
                                      ▼
                              ┌───────────────┐
                              │ GEMINI (cloud) │
                              │ Does the       │
                              │ actual task    │
                              └───────────────┘
```

## Components

### 1. SmolLM2 Summarizer
- Model: HuggingFaceTB/SmolLM2-1.7B via Cactus
- Input: First ~2000 tokens of file content
- Prompt: "Summarize this file content. Note any potentially sensitive information (names, emails, API keys, passwords, financial data, confidential terms)."
- Output: ~200 token summary
- Destroyed after use to free RAM

### 2. FunctionGemma Router
- Model: google/functiongemma-270m-it via Cactus
- Input: Summary from Step 1
- Tools:
  - `classify_safe()` — no sensitive data detected
  - `flag_pii(types: list[str])` — PII found, needs redaction (email, ssn, phone, api_key, password)
  - `block_transfer(reason: str)` — contains secrets/credentials, never send
  - `request_permission(reason: str)` — ambiguous content, escalate to Gemini + user
- Uses confidence score to validate decision

### 3. Python Executor (deterministic)
- `classify_safe` → pass file through unchanged
- `flag_pii` → regex-based redaction (email→[EMAIL_1], SSN→[SSN_1], etc.)
- `block_transfer` → return denial, log reason
- `request_permission` → send summary to Gemini for second opinion, present to user with options

### 4. Cloud Layer (Gemini)
- Receives ONLY sanitized/approved data
- Does the user's actual task (analyze, summarize, fix code, etc.)
- For ambiguous cases: receives summary only (not raw file), recommends action, user confirms

## Demo Files (samples/)

| File | Content | Expected Action |
|---|---|---|
| marketing_copy.txt | Clean public marketing text | SAFE — pass through |
| user_database.json | Fake emails, SSNs, phone numbers | SANITIZE — redact PII |
| api_config.env | Fake API keys, DB passwords | BLOCK — never send |
| partnership_agreement.txt | "Project Titan" references, ambiguous terms | ESCALATE — Gemini judges, user confirms |

## Demo UI (CLI)

```
$ python aegis.py "Analyze this file" samples/user_database.json

[AEGIS] Scanning file locally...
  Model: SmolLM2-1.7B | Time: 340ms
  Summary: "JSON with 50 user records: name, email, phone, ssn"

[AEGIS] Classifying sensitivity...
  Model: FunctionGemma | Time: 180ms
  Tool: flag_pii(types=["email", "ssn", "phone"])
  Confidence: 0.92 | Decision: SANITIZE

[AEGIS] Redacting PII locally...
  Replaced: 50 emails, 50 SSNs, 50 phone numbers

[AEGIS] Sending sanitized file to Gemini...
  Cloud model: gemini-2.5-flash
  Result: [analysis of the file without any real PII]
```

## Hackathon Scoring Alignment

| Judging Criteria | How Aegis Scores |
|---|---|
| Functionality & Execution | Working demo with 4 scenarios, real on-device inference |
| Hybrid Architecture & Routing | Routes on DATA SENSITIVITY not just model confidence. Three-tier: SmolLM2→FunctionGemma→Gemini |
| Agentic Capability | FunctionGemma reasons about data, calls tools, coordinates with cloud. Real agent behavior. |
| Theme Alignment | The BEST reason for local-first: privacy. Raw data never leaves. |

## Two Deliverables

1. **main.py** — optimized `generate_hybrid` for benchmark leaderboard (Gate 1: top 10)
2. **aegis.py** — the privacy layer demo (Gate 2: qualitative judging)

Both use the same Cactus + FunctionGemma + Gemini stack.

## Verification

1. Run `python aegis.py "Summarize" samples/marketing_copy.txt` → should pass through, no redaction
2. Run `python aegis.py "Fix bugs" samples/user_database.json` → should redact PII, send clean version
3. Run `python aegis.py "Review" samples/api_config.env` → should block entirely
4. Run `python aegis.py "Analyze" samples/partnership_agreement.txt` → should escalate to Gemini, prompt user
5. Run `python benchmark.py` → verify leaderboard score still works
