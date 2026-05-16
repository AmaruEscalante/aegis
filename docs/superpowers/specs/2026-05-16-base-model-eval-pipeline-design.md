# Base Model Eval Pipeline Design

**Date:** 2026-05-16
**Status:** Approved
**Author:** Christian Chavez
**Branch:** `ollama-migration`

## Goal

Build the synthetic data pipeline and generalized eval framework needed to make a **data-driven decision** about which classifier path Aegis should pursue. Run all 3 base models (FunctionGemma, EmbeddingGemma, gemma4:e2b) against a 200-example synthetic dataset + the 12 hand-curated real samples, produce a head-to-head scorecard, and use it to pick a training direction in a follow-up spec.

**This spec is explicitly NOT about training.** Training infrastructure for the chosen model becomes a separate Phase 2 spec after we see the eval numbers.

## Context

Phase 0 evals on 12 hand-curated samples gave us directional signal:

| Model | Accuracy | Macro F1 | Warm latency |
|---|---|---|---|
| `gemma4:e2b` | 58% | 0.51 | 7.6s/case |
| `functiongemma` (untuned) | 25% | 0.10 | 600ms/case |
| `embeddinggemma` (k=1 NN LOO-CV) | 75% | 0.65 | ~100ms/case |
| `gemma4:31b` (reference) | ~92% (7/8 smoke) | high | ~30s/case |

These numbers are useful but built on only 12 samples — too small a sample to make a confident training-direction decision. The synthetic dataset gives us ~17× more eval signal and serves double duty: it's also available as training data if Phase 2 wants it.

## Non-goals

- Training any classifier (LR head, MLP head, LoRA fine-tune). Phase 2.
- Modifying `aegis_bridge.py` or the wire contract. The bridge keeps using `gemma4:31b` (or whatever `--model` is set to) until Phase 2 picks a winner.
- Integrating trained classifiers into the middleware or backend.
- Producing publication-quality benchmarks. The goal is *internal* decision support, not external claims.

## Architecture

```
train/                              NEW directory
├── generate_dataset.py             Synthetic generator (uses GEMINI_API_KEY)
│                                   Reads scenarios from prompts.py, calls Gemini,
│                                   writes 200 (text, label) rows to dataset.jsonl
│
├── prompts.py                      Per-class system + scenario lists
│                                   50 scenarios × 4 classes = 200 generation tasks
│
├── dataset.jsonl                   Generated artifact (gitignored)
│                                   Schema: {"text": "<file content>", "label": "<verdict>",
│                                            "scenario_id": "<class>:<n>"}
│
└── README.md                       Regenerate / extend instructions

eval.py                             NEW, repo root
                                    Drives one base model through the full eval
                                    against a chosen split. Same scorecard format
                                    as Phase 0 benchmark.py.

docs/eval-results/
├── (Phase 0 logs already present)
├── 2026-05-XX-<model>-base.txt     Phase 1 per-model logs (new)
└── scorecard.md                    Auto-updated comparison: all 3 base models,
                                    all eval splits, latency + accuracy + F1
```

## Components

### `train/prompts.py` — scenario lists

Each verdict gets exactly **50 pre-defined scenarios** that drive Gemini generation. Each scenario is a short directive (e.g., "kubernetes_secrets.yaml with base64-encoded production database password"). Diversity is enforced *deterministically* — the scenarios are a hard-coded list, not generated.

**Scenario distribution (final list lives in `prompts.py`):**

- **classify_safe (50)** — examples to cover:
  - Open-source code: README.md (Python lib), README.md (JS lib), LICENSE, CONTRIBUTING.md, CHANGELOG.md
  - Public marketing: B2B one-pager, consumer app one-pager, press release, case study
  - Public docs: API reference page, tutorial, FAQ, public product spec
  - Public reports: published annual report excerpt, public market study
  - Code config without secrets: tsconfig.json, eslintrc, prettierrc
  - Public datasets: openly published sample CSV with NO PII
  - …(45 more variations across these themes)

- **flag_pii (50)** — examples to cover:
  - Customer DB (CSV with name/email/phone)
  - Patient records (CSV with DOB/SSN/medical-record-number)
  - Employee directory (JSON with name/phone/address/employee-ID)
  - HR records (CSV with salary, full name, SSN)
  - Mailing list (name + email)
  - Support tickets (customer name, account number, address)
  - Survey responses with identifying fields
  - Order history (shipping addresses, names, phone)
  - School enrollment (student names, DOB, addresses)
  - Insurance claims (claimant name, policy number, DOB)
  - …(40 more variations)

- **block_transfer (50)** — examples to cover:
  - `.env` file with AWS_SECRET_ACCESS_KEY, OPENAI_API_KEY, etc.
  - `.env` with DATABASE_URL containing password
  - kubernetes secrets.yaml with base64-encoded production creds
  - docker-compose.yml with hard-coded database/redis passwords
  - OAuth `client_secret.json`
  - SSH private key (`-----BEGIN OPENSSH PRIVATE KEY-----`)
  - SSL/TLS private key
  - GCP service-account JSON
  - AWS credentials file
  - `.npmrc` with auth tokens
  - Stripe live key in a config snippet
  - …(39 more variations)

- **request_permission (50)** — examples to cover:
  - NDA template
  - Partnership agreement
  - M&A Letter of Intent
  - Board meeting minutes with financial projections
  - "Confidential — Competitive Strategy" doc
  - Internal salary band
  - Layoff plan / RIF list
  - Trade-secret recipe / formula
  - Internal SWOT analysis
  - Vendor evaluation matrix (internal scoring)
  - Q3 financial forecast (pre-publication)
  - Confidential roadmap
  - …(38 more variations)

### `train/generate_dataset.py`

Reads `prompts.py`, calls Gemini per scenario, writes `dataset.jsonl`.

**Key behaviors:**
- One Gemini call per scenario (200 total). Estimated cost: ~$0.10-0.30 on Gemini 2.5 Flash.
- Per-scenario prompt template asks Gemini to produce *full file content* (not a summary): 500-3000 chars of realistic text in the appropriate file format (CSV, JSON, YAML, env, prose, etc.).
- Validates each output: must contain at least 300 chars, must not echo the scenario instruction back verbatim, must include format-appropriate features (e.g., flag_pii scenarios must contain at least one regex-detectable PII pattern).
- Retries with a different temperature on failed validation (up to 2 retries).
- Resumes from existing `dataset.jsonl` if interrupted (skip scenarios already written).
- Streams progress to stdout: `[ 47/200] block_transfer:23 (k8s secrets) — generated 1842 chars`.

**Failure mode:** If `GEMINI_API_KEY` is unset, fail loudly. If a scenario fails after retries, log it and continue (the eval can tolerate a small number of missing scenarios).

### `eval.py`

Generalized eval driver. Replaces `benchmark.py`'s role for Phase 1 (we keep `benchmark.py` around for compatibility with the 12-sample hand-curated path until Phase 2 cleanup).

**Interface:**

```bash
python eval.py --model <ollama-tag>                  # one model, all eval samples
python eval.py --model embeddinggemma --protocol knn # for embedding models
python eval.py --model gemma4:e2b --bridge-url ...   # generative models via bridge
python eval.py --all                                 # runs all 3 base models sequentially
python eval.py --warmup-calls 1                      # default 1; throwaway calls before timing
```

**Warm-up:** Before timing any case, the runner does N throwaway calls (default 1) so the first real measurement reflects warm-cache latency, not Ollama's model-load cost. The throwaway call's latency is logged separately as `cold_start_ms` in the per-model output but is **not** included in p50/p95/p99 calculations.

**Eval set composition:**

- All 12 hand-curated real samples from `samples/`
- **Eval set = 12 cases total.** Synthetic data is **not** in the eval set.

Rationale: The 200 synthetic samples in `train/dataset.jsonl` will be used as *training data* in Phase 2. Evaluating on data the model trained on (in Phase 2) would be data leakage. Keeping the eval set strictly to hand-curated real samples — held out from any training, in any phase — gives apples-to-apples comparisons across Phase 1 (base models) and Phase 2 (trained models).

Tradeoff acknowledged: 12 samples is a small eval set; F1 confidence intervals are wide. We accept this as a honest constraint of available labeled real data. If a Phase 1 result is ambiguous due to small-sample noise, we can hand-label more real samples before Phase 2.

**Per-model paths:**

| Model | Path | Notes |
|---|---|---|
| `gemma4:e2b` | Start bridge with `--model gemma4:e2b`, POST `/classify` per case | Already wired |
| `functiongemma` | Same as above with `--model functiongemma` | Already wired |
| `embeddinggemma` | Direct Ollama `/api/embed`, k-NN LOO-CV against labeled set | Extension of existing `eval_embeddinggemma.py` |

**Output per run:** `docs/eval-results/2026-05-XX-<model>-base.txt` with:
- Cold-start latency (one throwaway call, reported separately)
- Per-case rows (file, expected, predicted, confidence, latency_ms — all warm)
- Per-class P/R/F1
- Overall accuracy, macro F1
- Warm-call latency p50, p95, p99
- Confusion matrix

**Aggregate output:** `docs/eval-results/scorecard.md` updated with one row per model:

```markdown
| Model | Accuracy | Macro F1 | Cold start | p50 (warm) | p95 (warm) | Notes |
|---|---|---|---|---|---|---|
| gemma4:e2b (untuned)       | XX% | 0.XX | XXXms | XXXms | XXXms | False-negative bias |
| functiongemma (untuned)    | XX% | 0.XX | XXXms | XXXms | XXXms | Collapses to one class |
| embeddinggemma (k=1 NN)    | XX% | 0.XX | XXXms | XXXms | XXXms | Heterogeneous-safe failure |
| gemma4:31b (Phase 0 ref)   | 92% | —    | ~60s  | ~30s  | ~60s  | Production baseline |
```

All warm latencies are measured **after a single throwaway warm-up call**. Cold start is the throwaway call's wall time — useful operationally (will we keep models hot in Ollama's RAM?) but not a model-capability number.

## Data flow

```
prompts.py (50 × 4 scenarios)
    │
    ▼
generate_dataset.py
    │  POST Gemini 200×
    │  validate output
    │  write JSONL row
    ▼
train/dataset.jsonl (200 rows)
    │
    │  + samples/ (12 hand-curated rows)
    ▼
eval.py --model <tag>
    │  warm-up: 1 throwaway call (cold-start time recorded separately)
    │  for each row:
    │    POST /classify (generative) OR /api/embed + kNN (embedding)
    │    record (predicted, latency)
    │  compute P/R/F1, warm-call latency percentiles (p50/p95/p99)
    ▼
docs/eval-results/<date>-<model>-base.txt + scorecard.md
    │
    ▼
DECISION: pick training direction → Phase 2 spec
```

## What we measure

For each of the 3 base models on the **12-case eval set**:

| Metric | Why it matters |
|---|---|
| Overall accuracy | Sanity check; can it do the task at all? |
| Per-class precision / recall / F1 | Where does it fail? Symmetric failure (random) vs. bias (false-negatives)? |
| Macro F1 | Single number summary; weights all classes equally |
| Cold-start latency | Operational — model load time when Ollama swaps weights in. Reported once per model from the throwaway warm-up call. |
| Warm p50 / p95 / p99 latency | Production reality; tail matters more than average for a hot-path gate. Measured *after* warm-up so model-load is excluded. |
| Confusion matrix | Diagnostic — is the failure mode fixable with more training data, or architectural? |

## Decision criteria for Phase 2

After running Phase 1, we'll have a scorecard. The Phase 2 spec is written based on these heuristics:

- **EmbeddingGemma ≥ 85% accuracy and p95 < 500ms** → Phase 2 = train an LR/MLP head on the same dataset, ship as production classifier. This is the "modern embedding + head" path.
- **EmbeddingGemma < 85% but the failure mode is concentrated in one class** → Phase 2 = augment scenario coverage for the weak class, regenerate, re-eval, decide again.
- **All 3 base models underperform broadly** → Phase 2 = FunctionGemma LoRA fine-tune is the most architecturally promising rescue path. Use the 200-example dataset (or generate more).
- **Any base model already hits ≥ 92% (current prod baseline) at <500ms p95** → ship it as-is, skip training entirely.

We don't pre-commit to any of these branches; the scorecard data picks the branch.

## Error handling

- **`GEMINI_API_KEY` missing** — `generate_dataset.py` exits with a clear error and instructions.
- **Gemini rate limit / timeout** — retry up to 3× with exponential backoff. After 3 failures, skip the scenario and log it.
- **Ollama unreachable during eval** — `eval.py` aborts with a clear error pointing at `ollama serve`.
- **Invalid model tag** — Ollama returns 404; surface to user.
- **Empty dataset.jsonl** — `eval.py` refuses to run with <50 cases (insufficient signal).
- **Validation failure on >20% of generated examples** — abort generation, surface to user (likely prompt issue).

## Testing

- **Smoke test** for `generate_dataset.py`: run with `--limit 8` (2 per class) to verify Gemini integration and JSONL writes correctly. ~30 seconds, <$0.01 of Gemini cost.
- **Smoke test** for `eval.py`: run against a single model with a 4-sample test set (one per class, hand-picked). Verify output formatting matches the scorecard template.
- **Sanity check** the dataset post-generation: random-sample 5 examples per class, manually verify they're realistic and correctly labeled.

## Open questions

- **How realistic do the synthetic files need to be?** A "fake `.env`" is easy — it's just text. A "fake board meeting minutes" is harder — Gemini might produce something stilted. The scenario list in `prompts.py` includes enough specificity that Gemini should produce plausible content, but post-generation sanity check is essential.
- **Should the 12 hand-curated samples be used as few-shot examples in the Gemini prompts?** Pro: anchors the synthetic distribution to the real test distribution. Con: risks the test/eval anti-pattern where the eval set leaks into training. **Decision: no** — keep them strictly separate. The 12 real samples remain unseen by the generator.
- **What about file format diversity (CSV vs JSON vs YAML vs prose)?** The scenario list implicitly drives this — e.g., "kubernetes secrets YAML" produces YAML, "customer database export" produces CSV. Format diversity is a property of scenario diversity, not an explicit dimension to enumerate.

## Rollback plan

This phase is additive — generates files in new directories and writes new artifacts. No existing code is modified beyond `eval.py` being added at repo root. Rollback is simply:
- `rm -rf train/ eval.py docs/eval-results/2026-05-1*-*-base.txt`
- `git checkout` to recover anything inadvertently committed.

The `aegis-migration` branch's existing work (bridge + middleware + docs migration) is untouched.
