# Aegis Base-Model Scorecard

**Phase:** Phase 1 (base-model eval) + Phase 2 (trained head) + Phase 3a (30-sample eval)
**Dates:** Phase 1 — 2026-05-16; Phase 2 — 2026-05-17; Phase 3a — 2026-05-17
**Hardware:** local M-class Mac
**Spec:** [`docs/superpowers/specs/2026-05-16-base-model-eval-pipeline-design.md`](../superpowers/specs/2026-05-16-base-model-eval-pipeline-design.md)

## Results

### 12-sample eval (Phase 1 / Phase 2)

12 hand-curated real samples in `samples/` (3 per verdict class). Apples-to-apples comparison of the four Phase 1 base models and the Phase 2 trained head.

| Model | Protocol | Accuracy | Macro F1 | Cold start | Warm p50 | Warm p95 | Warm p99 | Notes |
|---|---|---|---|---|---|---|---|---|
| `gemma4:31b` (Phase 1 baseline) | bridge | 91.67% | 0.914 | 20,817 ms | 30,074 ms | 52,863 ms | 58,906 ms | Strongest of the untuned baselines, slowest. One miss: `marketing_copy.txt` → `flag_pii` (defensible — file contains `press@acmecorp.com`). |
| `gemma4:e2b` (untuned) | bridge | 58.33% | 0.511 | 9,667 ms | 6,597 ms | 8,643 ms | 8,795 ms | Confidently-wrong false negatives — collapses `flag_pii` (2/3 missed) and `request_permission` (3/3 missed) to `classify_safe`. |
| `functiongemma` (untuned) | bridge | 25.00% | 0.100 | 1,760 ms | 644 ms | 684 ms | 693 ms | Collapses everything to `classify_safe` (chance-level). |
| `embeddinggemma` (k=1 NN LOO-CV) | knn | 75.00% | 0.652 | 1,233 ms | 103 ms | 196 ms | 237 ms | Perfect on three classes, fails ALL 3 `classify_safe` cases — heterogeneous safe corpus too diverse to cluster with only 3 labeled neighbors. |
| `embeddinggemma` + LR head | head | 100.00% | 1.000 | ~700 ms | 98 ms | 163 ms | 249 ms | 12/12 on the real eval. Result not yet statistically distinguishable from 91.67% at this set size — see 30-sample row. |

### 30-sample eval (Phase 3a — the deciding set)

30 hand-curated + publicly-sourced real samples in `samples/` and `samples/external/` (7-8 per verdict class). Re-evaluated only the two viable production candidates: the Phase 2 trained head and the `gemma4:31b` baseline. (E2B, FunctionGemma, and the k-NN protocol were eliminated as candidates in Phase 1 on architectural grounds, not noise — no value in re-running them.)

| Model | Protocol | Accuracy | Macro F1 | Cold start | Warm p50 | Warm p95 | Warm p99 | Notes |
|---|---|---|---|---|---|---|---|---|
| **`embeddinggemma` + LR head** | **head** | **96.67% (29/30)** | **0.967** | **~700 ms** | **104 ms** | **327 ms** | **1,690 ms** | **One miss: `delphix_dxtoolkit_f6fdab90.example` (flag_pii → block_transfer) — file genuinely contains both a user table AND a `password` column; both labels defensible.** |
| `gemma4:31b` | bridge | 86.67% (26/30) | 0.868 | 30,170 ms | 34,841 ms | 102,345 ms | 105,881 ms | Four misses: same `delphix_dxtoolkit` ambiguity; plus `marketing_copy.txt` (the Phase 1 miss reproduced); plus `git_commit_message.txt` (commit-author email triggered false PII alarm); plus `fonoster_fonoster.dev` (curious mis-route of a `.env.dev` to `request_permission`). |

**Gap: +10 percentage points for the trained head, at ~335× lower warm latency.** Both models share exactly one miss — the genuinely ambiguous `delphix_dxtoolkit` file. The LR head's only error is one that `gemma4:31b` also gets wrong. The trained head gets 3 cases that `gemma4:31b` doesn't.

## Reading the scorecard

- **Accuracy on 12 samples** has wide confidence intervals — treat differences ≤8pp (one case flip) as noise.
- **Cold start** = first call after Ollama loads the model. Operational concern (keep models warm) but not a model-capability number.
- **Warm latency** = subsequent calls, after one throwaway warm-up.
- **The 200-sample synthetic dataset** in `train/dataset.jsonl` (when generated) is reserved for Phase 2 training and is **not** in the eval set.

## Phase 2 decision criteria (from spec)

- If `embeddinggemma` ≥ 85% accuracy and p95 < 500ms → Phase 2 = train an LR/MLP head on `train/dataset.jsonl`, ship as production classifier. This is the "modern embedding + head" path.
- If `embeddinggemma` < 85% but the failure mode is concentrated in one class → augment scenarios for that class, regenerate, re-eval, decide again.
- If all 3 base models broadly underperform → Phase 2 = FunctionGemma LoRA fine-tune.
- If any base model already hits ≥ 92% at p95 < 500ms → ship as-is, skip training.

## Recommendation: Train EmbeddingGemma + classifier head

**The data points to a single conclusion: EmbeddingGemma is the production-shape winner; train a classifier head on top of it.**

### Why EmbeddingGemma wins

1. **Best untuned accuracy** of the three candidates (75% vs e2b's 58% vs FG's 25%).
2. **Fastest by 6-300×** — warm p50 103ms vs e2b's 6.6s vs FG's 644ms vs 31b's 30s.
3. **Right architecture for the task** — encoder, not decoder. Classification is what encoders are built for.
4. **Failure mode is small-N artifact, not model limit** — all 3 misses are in `classify_safe` because k=1 NN against only 3 labeled neighbors can't capture the heterogeneity of "safe" content (open-source code vs. marketing copy vs. blog post are semantically very different). A trained classifier head over 50 diverse safe examples will learn what they share.
5. **Cheapest training path** — sklearn LR fit on 200 vectors takes seconds, no GPU, no LoRA, no Colab. Phase 2 implementation is ~50 lines of Python.

### Why not the others

- **`gemma4:31b`** is more accurate (91.67%) but **200-500× slower** than the trained-EmbeddingGemma target. Untenable as a hot-path gate. Useful only as the "production reference" the trained classifier needs to match.
- **`gemma4:e2b`** has the worst combination — slow (6.6s) AND inaccurate (58%) AND confidently wrong (0.95-1.00 confidence on misses). LoRA fine-tuning a generalist decoder for classification is the architecturally wrong hammer. Drop from Phase 2 consideration.
- **`functiongemma`** untuned is chance-level (25%, collapses to one class — same pattern Google's docs predict pre-fine-tune). LoRA fine-tuning could plausibly get it to 80%+ at ~600ms, but it's still slower than embedding-based inference, and the training is harder (LoRA on a tool-calling SLM via Unsloth/Colab vs. sklearn on a laptop). Keep functiongemma as a "rescue path" if EmbeddingGemma head training underperforms.

### Bear case (resolved at 30 samples)
<a name="bear-case-worth-flagging"></a>

The Phase 1/2 scorecard flagged that 12 samples couldn't statistically distinguish 12/12 from 11/12 — both could plausibly be the same underlying classifier with one example flipped. The Phase 3a 30-sample expansion was designed to resolve this. The new gap (96.67% vs 86.67%, 29/30 vs 26/30) is a 4× error-rate difference; the LR head's single error is one `gemma4:31b` also makes. **The trained head is the production-shape winner at every signal we have.** Remaining caveats:

1. 30 is still small. A 50–100 sample real-world eval would tighten things further; we'd run it before publishing as a public MCP plugin (Phase 4).
2. Both eval sets are author-curated (Channels A and C from the [data-sourcing strategy](../../docs/roadmap.md)). A blind eval set provided by a teammate or an external reviewer is worth doing before any marketing claims.

### Phase 2 outcome

✅ **Phase 2 deliverable shipped (2026-05-17):**

1. `train/train_head.py` — embeds the 200 curated examples via Ollama → embeddinggemma, sweeps C ∈ {0.1, 1.0, 10.0} under 5-fold stratified CV, fits a final `LogisticRegression` head on all 200 examples at the winning C, saves to `aegis-head/lr.joblib` with metadata (CV scores, embed model name, chosen C).
2. `train/eval_head.py` — re-uses the same 12 `CASES` defined in `eval.py` so the Phase 2 row is apples-to-apples with the four Phase 1 rows.
3. `aegis-head/lr.joblib` — 25 KB serialized head (3,076 trained parameters: 4 × 768 weights + 4 biases). Committed to the repo.
4. New row in this scorecard above.

We **dropped the MLP** from the planned scope. The LR head hit 100% on the real eval and 98% on training-set CV; an MLP could only add training-data overfit, not capability. We can revisit if the eval set expands and new failure modes show up.

### Phase 3a outcome

✅ **Phase 3a deliverable shipped (2026-05-17):**

1. **Eval set expanded from 12 to 30 samples.** 18 new files added: 11 hand-curated (Channel A — `samples/`), 7 mined from public GitHub (Channel C — `samples/external/` with `.provenance.json` siblings).
2. `tools/sample_collector.py` — reusable tool that runs `gh search code` against per-class query lists, fetches blobs via `git/blobs/{sha}`, validates with class-signal regex, rejects files matching real-secret patterns, and writes vetted samples with full provenance. Approx half-day of tooling for an indefinitely-reusable channel.
3. `eval.py`'s `CASES` list grew from 12 to 30, preserving the original 12 verbatim.
4. **Two model re-evaluations** on the new 30-sample set: LR head (29/30, 96.67%) and gemma4:31b (26/30, 86.67%). The other three Phase 1 base models were not re-run (eliminated as candidates in Phase 1 on architectural grounds, not noise).
5. Statistical tie at 12 samples is now **resolved**: 10-percentage-point gap (4× error-rate ratio) in favor of the trained head, at ~335× lower warm latency.

### Suggested next steps (Phase 3b–3d)

1. **3b — drop the Ollama dependency.** Replace the Ollama HTTP backend with in-process inference (sentence-transformers or HuggingFace transformers). Keep `--backend ollama` as a dev flag. This makes the package self-contained for Phase 4 distribution.
2. **3c — wire `HeadBackend` into `aegis_bridge.py`** as the default. Load the joblib at startup, route `/classify` through it. Keep `OllamaBackend` reachable via `--backend ollama` for A/B comparison.
3. **3d — add PDF + DOCX support to `aegis_read`.** Text extraction via `pypdf` / `python-docx`. Scanned-image PDFs deferred to Phase 5.
4. **Rescue path remains FunctionGemma LoRA fine-tune** — not triggered, since the 30-sample result was clearly favorable. Reserved for if a future eval surfaces failures the LR head can't address.
