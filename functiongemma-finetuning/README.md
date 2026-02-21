# FunctionGemma Fine-Tuning for Aegis

## Goal

Fine-tune `google/functiongemma-270m-it` to reliably classify file summaries into one of four privacy actions by calling the correct tool. This is for the **Aegis** project — a local privacy layer that intercepts files before they reach cloud AI agents.

## The Problem

Out-of-the-box FunctionGemma (270M params) ignores system prompt instructions and defaults to calling `block_transfer` regardless of file content. It needs to learn our specific 4-tool classification task.

## Model

- **Base model**: `google/functiongemma-270m-it` (270M params, Gemma 3 architecture)
- **Method**: LoRA fine-tuning via Unsloth
- **Target**: Learn to map file security summaries → correct privacy tool call

## The 4 Privacy Tools

| Tool | When to call | Example trigger |
|---|---|---|
| `classify_safe(reason)` | File has no sensitive data | "Marketing copy, public metrics, no PII" |
| `flag_pii(types)` | File contains PII that can be redacted | "Contains emails, SSNs, phone numbers" |
| `block_transfer(reason)` | File contains secrets that must never leave | "Contains API keys, DB passwords, tokens" |
| `request_permission(reason)` | Ambiguous/confidential content needs human review | "Confidential agreement, trade secrets" |

## Architecture Context

```
User file
    |
    v
SmolLM2-1.7B (summarizer, local) -- produces a 2-3 sentence summary
    |
    v
FunctionGemma-270M (THIS MODEL) -- reads summary, calls correct privacy tool
    |
    v
Python executor -- runs regex redaction, blocks, passes through, or escalates
    |
    v
Gemini (cloud) -- only receives sanitized/approved data
```

FunctionGemma's job is simple: **read a file summary, pick the right tool, provide arguments**.

## Training Data Format

FunctionGemma uses Gemma 3's chat template with special tokens for tool calling:

```
<bos><start_of_turn>user
You are a privacy classifier. Based on the file summary, call the correct tool.

File summary:
{summary text}
<end_of_turn>
<start_of_turn>model
<start_function_call>call:classify_safe{reason: <escape>public marketing content with no sensitive data<escape>}<end_function_call>
<end_of_turn>
```

## Dataset

See `dataset.jsonl` — ~200 examples across all 4 categories:
- ~60 safe examples (public docs, marketing, README files, open-source code)
- ~60 PII examples (user databases, HR records, customer lists, medical records)
- ~40 block examples (config files, .env files, credentials, private keys)
- ~40 escalate examples (contracts, NDAs, internal memos, financial reports)

## Fine-Tuning Steps

### 1. Upload to Google Colab
Upload this folder to Colab or mount from Google Drive.

### 2. Install dependencies
```python
!pip install unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git
```

### 3. Run training
```python
# See train.py for the full script
python train.py
```

### 4. Export adapter
The LoRA adapter will be saved to `./aegis-adapter/`

### 5. Convert for Cactus (on your Mac)
```bash
cactus convert google/functiongemma-270m-it ./aegis-functiongemma --lora ./aegis-adapter
```

### 6. Update aegis.py
Change `FUNCTIONGEMMA_PATH` to point to `./aegis-functiongemma`

## Expected Outcome

After fine-tuning, FunctionGemma should:
- Call `classify_safe` for clearly public/harmless content
- Call `flag_pii` when emails, SSNs, phones, addresses are mentioned
- Call `block_transfer` for API keys, passwords, credentials, private keys
- Call `request_permission` for NDAs, contracts, trade secrets, internal docs
- Include a meaningful `reason` or `types` argument explaining the decision
