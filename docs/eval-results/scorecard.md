# Aegis Base-Model Scorecard

**Phase:** Phase 1 (base-model eval, no training)
**Eval set:** 12 hand-curated real samples in `samples/` (3 per verdict class)
**Date:** 2026-05-16
**Hardware:** local M-class Mac
**Spec:** [`docs/superpowers/specs/2026-05-16-base-model-eval-pipeline-design.md`](../superpowers/specs/2026-05-16-base-model-eval-pipeline-design.md)

## Results

| Model | Protocol | Accuracy | Macro F1 | Cold start | Warm p50 | Warm p95 | Warm p99 | Notes |
|---|---|---|---|---|---|---|---|---|
| `gemma4:31b` (current prod) | bridge | **91.67%** | 0.914 | 20,817 ms | 30,074 ms | 52,863 ms | 58,906 ms | Strongest accuracy, slowest. One miss: marketing_copy.txt → flag_pii (defensible — file contains `press@acmecorp.com`). |
| `gemma4:e2b` (untuned) | bridge | 58.33% | 0.511 | 9,667 ms | 6,597 ms | 8,643 ms | 8,795 ms | Confidently-wrong false negatives — collapses flag_pii (2/3 missed) and request_permission (3/3 missed) to classify_safe. |
| `functiongemma` (untuned) | bridge | 25.00% | 0.100 | 1,760 ms | 644 ms | 684 ms | 693 ms | Collapses everything to classify_safe (chance-level). Tool-calling SLM with zero task knowledge until fine-tuned (Google docs report 58% → 85% after fine-tune on the Mobile Actions benchmark). |
| `embeddinggemma` (k=1 NN LOO-CV) | knn | 75.00% | 0.652 | 1,233 ms | **103 ms** | 196 ms | 237 ms | Perfect on flag_pii, block_transfer, request_permission. Fails ALL 3 classify_safe cases — heterogeneous safe corpus (README, marketing, blog) too diverse to cluster with only 3 labeled neighbors. |

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

The eval set is **12 samples**. F1 confidence intervals are wide. If Phase 2 training pushes EmbeddingGemma + head to 11/12 or 12/12, that's not statistically distinguishable from the 91.67% baseline. To make a confident production decision, we may need to hand-label ~30-50 additional real samples before declaring victory.

### Suggested Phase 2 spec scope

1. Dataset is ready (`train/curated_data.py` → 200 hand-curated examples, 50/class; regenerates `train/dataset.jsonl` in ~1s). See `train/README.md` for the secret-placeholder policy used to keep `block_transfer` examples push-protection-safe.
2. Write `train/train_head.py` — embed all 200 samples via the Ollama embeddinggemma endpoint, fit sklearn LR + a small PyTorch MLP, save weights to `aegis-head/`. Report eval on the 12 real `samples/` files for both heads.
3. Add `HeadBackend` to `aegis_bridge.py` that loads the LR weights and serves classification at ~50-150ms end-to-end (embed via Ollama + LR predict in-process).
4. Update middleware contract handling (fixed reason strings per class — see design spec).
5. Decision gate after step 2: if both heads underperform on the 12 real samples (<85% acc), pivot to FunctionGemma LoRA fine-tune as the rescue path. Otherwise ship the better of LR vs. MLP.
