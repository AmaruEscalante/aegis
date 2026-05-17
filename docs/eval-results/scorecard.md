# Aegis Base-Model Scorecard

**Phase:** Phase 1 (base-model eval) + Phase 2 (trained head)
**Eval set:** 12 hand-curated real samples in `samples/` (3 per verdict class)
**Dates:** Phase 1 — 2026-05-16; Phase 2 — 2026-05-17
**Hardware:** local M-class Mac
**Spec:** [`docs/superpowers/specs/2026-05-16-base-model-eval-pipeline-design.md`](../superpowers/specs/2026-05-16-base-model-eval-pipeline-design.md)

## Results

| Model | Protocol | Accuracy | Macro F1 | Cold start | Warm p50 | Warm p95 | Warm p99 | Notes |
|---|---|---|---|---|---|---|---|---|
| `gemma4:31b` (current prod) | bridge | 91.67% | 0.914 | 20,817 ms | 30,074 ms | 52,863 ms | 58,906 ms | Strongest accuracy of the untuned baselines, slowest. One miss: `marketing_copy.txt` → `flag_pii` (defensible — file contains `press@acmecorp.com`). |
| `gemma4:e2b` (untuned) | bridge | 58.33% | 0.511 | 9,667 ms | 6,597 ms | 8,643 ms | 8,795 ms | Confidently-wrong false negatives — collapses `flag_pii` (2/3 missed) and `request_permission` (3/3 missed) to `classify_safe`. |
| `functiongemma` (untuned) | bridge | 25.00% | 0.100 | 1,760 ms | 644 ms | 684 ms | 693 ms | Collapses everything to `classify_safe` (chance-level). Tool-calling SLM with zero task knowledge until fine-tuned (Google docs report 58% → 85% after fine-tune on the Mobile Actions benchmark). |
| `embeddinggemma` (k=1 NN LOO-CV) | knn | 75.00% | 0.652 | 1,233 ms | 103 ms | 196 ms | 237 ms | Perfect on `flag_pii`, `block_transfer`, `request_permission`. Fails ALL 3 `classify_safe` cases — heterogeneous safe corpus (README, marketing, blog) too diverse to cluster with only 3 labeled neighbors. |
| **`embeddinggemma` + LR head** | **head (Phase 2)** | **100.00%** | **1.000** | **~700 ms** | **98 ms** | **163 ms** | **249 ms** | **12/12 on the real eval. 5-fold CV macro-F1 on training set = 0.980 @ C=10.0. Head is 25 KB (`aegis-head/lr.joblib`). 300× faster than `gemma4:31b`, ties or beats on accuracy. See [Bear case](#bear-case-worth-flagging).** |

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

### Bear case worth flagging
<a name="bear-case-worth-flagging"></a>

The eval set is **12 samples**. F1 confidence intervals are wide. The trained-head 12/12 result is best-in-class on this set, but the gap from 11/12 (the `gemma4:31b` baseline) is exactly one example — within the statistical noise floor. To make a confident production decision, we'd want ~30–50 additional hand-labeled real samples. The 5-fold cross-validation macro-F1 of 0.980 on the 200 training examples is corroborating evidence that the trained head generalizes, but neither number on its own definitively beats the LLM baseline.

### Phase 2 outcome

✅ **Phase 2 deliverable shipped (2026-05-17):**

1. `train/train_head.py` — embeds the 200 curated examples via Ollama → embeddinggemma, sweeps C ∈ {0.1, 1.0, 10.0} under 5-fold stratified CV, fits a final `LogisticRegression` head on all 200 examples at the winning C, saves to `aegis-head/lr.joblib` with metadata (CV scores, embed model name, chosen C).
2. `train/eval_head.py` — re-uses the same 12 `CASES` defined in `eval.py` so the Phase 2 row is apples-to-apples with the four Phase 1 rows.
3. `aegis-head/lr.joblib` — 25 KB serialized head (3,076 trained parameters: 4 × 768 weights + 4 biases). Committed to the repo.
4. New row in this scorecard above.

We **dropped the MLP** from the planned scope. The LR head hit 100% on the real eval and 98% on training-set CV; an MLP could only add training-data overfit, not capability. We can revisit if the eval set expands and new failure modes show up.

### Suggested next steps

1. **Expand the eval set** to ~30–50 real samples to break the 11/12-vs-12/12 statistical tie. Hand-label new files in `samples/` covering edge cases the current 12 don't reach (mixed-class files, near-boundary examples, multilingual content).
2. **Wire `HeadBackend` into `aegis_bridge.py`** — load the joblib at startup, expose it via `/classify` alongside (or replacing) the current `OllamaBackend`. Keep `gemma4:31b` reachable via a flag for A/B comparison.
3. **Middleware contract handling** (per design spec) — fixed reason strings per class.
4. **Rescue path remains FunctionGemma LoRA fine-tune** if the expanded eval set surfaces failures the LR head can't address.
