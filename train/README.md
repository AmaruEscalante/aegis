# Training Dataset

Builds `train/dataset.jsonl` — 200 labeled examples (50 per verdict class) used for Phase 2 training of the Aegis privacy classifier. **Not used at eval time** (eval runs on `samples/`).

## Quick start

```bash
python3 train/curated_data.py
```

Produces `train/dataset.jsonl` from the hand-curated Python source. Deterministic, 100% offline, no API keys, ~1 second.

Each row:
```json
{"scenario_id": "block_transfer:7", "label": "block_transfer", "text": "<file content>"}
```

## Why hand-curated (and not SLM-generated)

`train/generate_dataset.py` was the original Ollama-backed generator. We ran it once and the output suffered visible pattern collapse — identical README skeletons, recurring fake names, near-duplicate NDA structures, identical license-header typos. SLM-generated training data isn't varied enough to train a classifier that generalizes.

`train/curated_data.py` replaces it: 200 examples written by hand, deliberately heterogeneous in length, voice, file format, naming pool, and industry. `generate_dataset.py` is kept in-tree as documentation of the validator/regex coverage but is **not** the production path. The single source of truth is `curated_data.py`.

## Why block_transfer secrets are placeholders (not real-format strings)

The 50 `block_transfer` examples imitate `.env` files, k8s secrets, OAuth dumps, PEM keys, etc. — exactly the surfaces real leaked credentials show up in. When we tried committing earlier random-looking strings (`AKIA…` with 16 random chars, `sk_live_…` with high-entropy body), GitHub Push Protection rejected the push because its secret scanner could not distinguish synthetic from real.

The committed examples use:
- **AWS access keys** — AWS's documented canonical examples (`AKIAIOSFODNN7EXAMPLE`, `AKIAI44QH8DHBEXAMPLE`) and the matching documented secret keys (`wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`, `je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY`). These are on GitHub's allowlist.
- **Stripe keys** — `sk_test_PLACEHOLDER_NOT_A_REAL_KEY_…` style. Underscores in the body break Stripe's `[A-Za-z0-9]{24+}` detector pattern while leaving the env-var context (`STRIPE_SECRET_KEY=…`) intact.
- **Everything else** (`ghp_`, `glpat-`, `npm_`, `xoxb-`, `SG.…`, `AIza…`, etc.) — low-entropy `XXXX…` placeholders. Detectors with checksum validation reject these; pattern-only detectors with entropy filters skip them.

**Implication for training:** the classifier learns from the file structure around the credential (var name, file shape, context lines) — not from the high-entropy body of the secret itself. This is the right invariant: at inference, real leaked credentials have unpredictable bodies, and we want the classifier triggering on context, not memorized tokens.

**Implication if you extend the dataset:** if you add new `block_transfer` examples that contain real-format secrets (random AWS keys, real Stripe `sk_live_`, etc.), the push will be rejected. Use the placeholder conventions above.

## Validation

`curated_data.py` runs lightweight asserts at module-load time (per-class counts, length floors). For deeper validation (regex coverage on PII / secret patterns), see the patterns in `train/generate_dataset.py`.

## Files

- `curated_data.py` — single source of truth for the 200 examples. Run it to regenerate `dataset.jsonl`.
- `prompts.py` — scenario coverage list (50 × 4 classes) used by `generate_dataset.py`. Not consumed by `curated_data.py` but kept in sync as the coverage spec.
- `generate_dataset.py` — legacy Ollama-backed generator. Not the production path. Kept for reference and as a validator-regex library.
- `dataset.jsonl` — generated output, gitignored.
