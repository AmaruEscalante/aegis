# Synthetic Dataset Generator

Builds `dataset.jsonl` — labeled file content for Phase 2 training of the Aegis privacy classifier. **Not used at eval time** (eval runs on `samples/`).

## Quick start

Requires a local Ollama instance with `gemma4:e2b` pulled (or pass `--model <other>`).

```bash
# Phased rollout — run each stage, eyeball quality between them.
python train/generate_dataset.py --limit 2   # stage 1: 8 examples
python train/generate_dataset.py --limit 4   # stage 2: 16 examples
python train/generate_dataset.py             # stage 3: 200 examples

# Higher quality (slower):
python train/generate_dataset.py --model gemma4:31b
```

Subsequent runs **append** to the file. If you want to start over, `rm train/dataset.jsonl` first.

## What's generated

- Each row of `dataset.jsonl`:
  ```json
  {"scenario_id": "block_transfer:7", "label": "block_transfer", "text": "<file content>"}
  ```
- 4 verdict classes × up to 50 scenarios = up to 200 examples.
- Scenario list lives in `train/prompts.py` — edit there to extend or change coverage.

## Validation

Each generated example is checked against class-specific rules:
- All: length ≥ 300 characters, doesn't echo the scenario instruction.
- `flag_pii`: must contain at least one regex-detectable PII pattern (email, SSN, phone, US address).
- `block_transfer`: must contain at least one secret-hint pattern (AWS/Stripe/OpenAI/GitHub/PEM/`password=`/etc.).

Validation failures retry with a different temperature up to 2 times before giving up on that scenario. Failed scenarios are listed at the end of the run and the script exits 1.

## Wall time (approx, local Ollama on M-class Mac)

| Stage | Examples | `gemma4:e2b` | `gemma4:31b` |
|---|---|---|---|
| Stage 1 (--limit 2) | 8 | ~1 min | ~5 min |
| Stage 2 (--limit 4) | 16 | ~2 min | ~10 min |
| Stage 3 (full) | 200 | ~15-20 min | ~2-3 hours |

100% local, no API key, no cost.
