# Aegis — Limits and Improvement Paths

**Last updated:** 2026-05-22
**Purpose:** A standing reference for where Aegis's current accuracy ceiling comes from, what we believe the underlying walls are, and which concrete levers can move the number. Updated after each phase that changes the picture.

This doc is the place to come back to when planning a new accuracy push. The per-phase narrative lives in [`scorecard.md`](eval-results/scorecard.md); the roadmap is in [`roadmap.md`](roadmap.md); this doc is **strategic context** — what we believe is true about Aegis's ceiling and what we'd do about it.

## Current state (the floor we're holding)

**Shipped head:** `embeddinggemma-300m` + sklearn `LogisticRegression`, `prompt="none"`, `C=10.0`, trained on 200 hand-curated rows.

| Metric | Value | Source |
|---|---|---|
| Accuracy | **93/98 = 94.90%** | Phase 3b 98-sample held-out |
| Wilson 95% CI | [88.6%, 97.8%] | Same |
| Macro F1 | 0.949 | Same |
| CV macro-F1 (train) | 0.9799 | 5-fold stratified on 200 rows |
| Warm p50 latency | ~78–104 ms | M-class Mac, in-process |
| Warm p95 | ~216 ms | Same |
| Cold start | ~700 ms | Model load |

## What we've tried (compressed history)

The full history is in [`scorecard.md`](eval-results/scorecard.md). The compressed version:

| Phase | Approach | Held-out accuracy | Outcome |
|---|---|---|---|
| 1 | `gemma4:31b` baseline | 91.67% / 12 (30 s p50) | Too slow, dropped as hot-path |
| 1 | k-NN over embeddinggemma | 75% / 12 | Small-N artifact, dropped |
| 2 | LR head, 12-sample eval | 100% / 12 | Statistically tied at small N |
| 3a | LR head, 30-sample eval | 96.67% (29/30) | Shipped |
| 3b | LR head + `classify_doc` prompt | 88/98 = 89.80% | **Failed gate** — held-out reuse debt |
| 3b | LR head, no-prompt (rollback) | **93/98 = 94.90%** | **Shipped (current)** |
| 3b.5 | LR head, retrained on 214 + new held-out | 90/107 = 84.11% | **Failed gate, rolled back** |

## The three walls

These are the bottlenecks we believe — based on actual evidence from the phases — are limiting accuracy. They are NOT model-architecture limitations (EmbeddingGemma + LR is sufficient to hit 95%+; Phase 3b proves this). They are data/labeling limitations.

### Wall 1 — Training set size (200 rows)

**Evidence:** Phase 3b.5 added 14 rows (+7%) and produced a measurable −2 pp regression on the same 98-sample held-out, with 3 previously-correct must-not-regress cases (tambo, denysdovhan, MarekWo) flipping from `block_transfer` to `classify_safe`. A 7% training-data change should not flip 3 correct cases. That fragility says the boundary the head is learning is on the edge of statistical power.

**Implication:** Until the training set is large enough that small per-example labeling decisions don't ripple into accuracy swings, we are vulnerable to labeling judgment calls (see Wall 2). 200 rows / 4 classes = 50 per class is below the threshold where logistic regression heads stabilize for nuanced multi-class boundaries.

**Heuristic:** want ≥ 100 rows per class, ideally 200, to get under the fragility threshold. So 400-800 rows total.

### Wall 2 — Class boundary ambiguity at `classify_safe`/`request_permission`

**Evidence:** Phase 3b.5's failure was dominated by 13 NDA-template files (legal contract templates with placeholder `[Disclosing Party]` / `{{Effective Date}}` markers) being over-escalated as `request_permission`. The reviewer who flagged these as mis-labeled `request_permission` and recommended relabeling to `classify_safe` was correct in isolation — those files ARE publicly shareable templates. But moving them in the held-out, combined with the new training rows, pushed the model's decision boundary in a way that broke `.example` recognition elsewhere.

**The real ambiguity:** NDA templates are publicly shareable (classify_safe) but they're also the kind of thing a paralegal would flag if a co-worker pasted into Slack (request_permission). The 4-class verdict system forces a hard call on a genuinely ambiguous category. Any binary label is wrong some of the time.

**Implication:** This isn't fixable by more data alone. Either (a) we accept that NDA templates will be a noisy boundary case and design the eval set to reflect that honestly, or (b) we add a class / a confidence dimension to the output.

### Wall 3 — `.example`-shaped credential files at `classify_safe`/`block_transfer`

**Evidence:** The original Phase 3b held-out had 14 `.env`/`.example` files — 13 labeled `block_transfer`, 1 `flag_pii`. The training set had ONE `.env`-shaped row total. Phase 3b's failure mode (owid `.example-full` predicted classify_safe — the single fail-open) was the model not having seen enough mixed-placeholder/real-value `.env` files to recognize them. Phase 3b.5 tried to fix this by adding 7 `.env.example`-shaped training rows, but the boundary shifted in the wrong direction — 3 previously-correct files flipped to classify_safe.

**The real ambiguity:** A `.env.example` file with `your-api-key-here` is a template (classify_safe). The same file with `sk_live_<random hex>` is a credential dump (block_transfer). In real public-GitHub data, files are often midway — placeholder names BUT dev-defaulted values (`db_password=postgres`). Reasonable people disagree on the label.

**Implication:** Same as Wall 2 — partially fixable by more training data, partially a class-design issue. The "owid-shape" case (empty placeholders + dev defaults like `postgres/postgres`) is genuinely ambiguous.

## Improvement levers (in order of expected lift per unit cost)

These are **projections**, not measurements. The values are based on order-of-magnitude reasoning from the phases above and standard ML scaling intuitions; they are NOT eval-verified.

### Lever A — Expand training set to 500–1000 rows
**Expected lift:** +2 to +4 pp on diverse held-outs
**Cost:** 1-2 weeks of focused curation; ~$0 in compute
**What it fixes:** Wall 1 directly. Reduces fragility around small per-example labeling decisions. Partially mitigates Walls 2-3 by giving the model more examples of each ambiguous shape.
**Risk:** Curation quality matters more than quantity. 500 rows of careful Channel A + C mining beats 1000 rows of regex-mined fluff. The 3b.5.1 follow-up spec covers some of this.

### Lever B — Confidence-thresholded abstain
**Expected lift:** Eliminates most fail-opens at small recall cost
**Cost:** ~2 days. Implement at the bridge layer: if max(softmax) < threshold (e.g., 0.6), default to `request_permission` (human review) instead of the argmax.
**What it fixes:** Wall 2 + Wall 3 partially. Doesn't change accuracy on confident cases; converts confident-wrong fail-opens into human-review escalations.
**Risk:** UX cost — too many escalations annoy users. Calibrate the threshold via the regression suite + a measured trade-off curve.

### Lever C — Active learning loop
**Expected lift:** Cumulative — ongoing rather than one-shot. Each retrain cycle moves the boundary closer to real production distribution.
**Cost:** Infra to log classifications + confidences; weekly labeling triage; monthly retrain pipeline. Probably 2-3 weeks of plumbing, then ongoing.
**What it fixes:** Walls 1-3 over time. Production data shows us boundary cases users actually encounter, not the boundary cases we imagined.
**Risk:** Requires Aegis to be deployed somewhere we can collect data — premature for current state.

### Lever D — Multi-head ensemble (per-domain heads)
**Expected lift:** +1 to +2 pp + cleaner per-class precision
**Cost:** ~1 week. Train separate LR heads for env-shape files, prose docs, structured data (CSVs). At inference, route via a cheap classifier (e.g., file-extension + content-shape heuristic) to the right head.
**What it fixes:** Wall 3 directly (the env-shape head can specialize). Mild help on Wall 2.
**Risk:** Adds architectural complexity. The single-head story is currently a strength of the marketplace pitch.

### Lever E — Larger embedder (Qwen3-Embedding-4B or similar)
**Expected lift:** +1 to +3 pp on truly held-out
**Cost:** ~1 week + a 4-8× latency hit (p50 jumps from ~80ms to ~300-600ms). Breaks the "fast" half of the value prop.
**What it fixes:** Adds representational capacity. Could help with subtle boundary distinctions that 768-dim embeddinggemma blurs.
**Risk:** Latency regression makes Aegis less competitive. Only worth it if accuracy ceiling becomes the dominant complaint AND latency budget loosens.

## Ceiling estimate

Honest read on where the head can plausibly go:

- **~96-97%** is achievable with Lever A alone (more training data). High confidence.
- **~97-98%** needs Lever A + B (data + confidence thresholding). The Wall 2/3 ambiguity caps how high pure accuracy can go without abstention.
- **>98%** probably needs architectural change (Lever D or E) OR accepting abstention/escalation as a feature, not a bug.

The wall to be honest about: **publishing a number above 97% on a real-world diverse held-out without ensemble or abstention is unlikely** because the underlying labeling task has irreducible ambiguity in places. The accuracy gap between "the model is right" and "reasonable people would disagree on the right label" closes around there.

## What's NOT a wall

Worth being clear what we're NOT bottlenecked by:

- **Embedder quality.** EmbeddingGemma's 768-dim representations carry the signal. Phase 3b proves it.
- **Head architecture.** Logistic regression is fine; an MLP would not help with the failures we have (the failures are about which class boundary to draw, not whether LR can fit the boundary).
- **Latency.** ~78ms p50 is comfortably under any reasonable interactive threshold.
- **Encoder fine-tuning.** Reserved as a "Phase X rescue path" in the roadmap. Fine-tuning the encoder is expensive, risks losing general representation quality, and won't help with labeling-decision walls.

## Open questions / things to revisit

1. **Is there a "5th class" worth adding?** "Ambiguous template" / "review when shared externally" — splits the load between classify_safe and request_permission for legal-template content. Would change the model surface and the user UX.
2. **What's the cost-benefit of moving to confidence scores in the output?** Today the bridge returns a single verdict. Returning `(verdict, confidence)` lets the MCP layer make policy decisions (e.g., "if confidence < 0.7 on classify_safe, prompt user").
3. **Could synthetic training data help?** The Phase 1 dataset.jsonl was supposed to be synthetic but Phase 2 went hand-curated. With a stronger generation model in 2026, could we generate 5K rows of high-quality boundary-case training data via a generation prompt + filtering pipeline? Worth ~1 weekend experiment.
4. **Channel B (the developer's own dev directories, anonymized) — still unexplored.** Could yield the highest-signal training data per the [roadmap's data-sourcing strategy](roadmap.md#channel-b--your-own-dev-directories-anonymized). Deferred for privacy/anonymization-effort reasons.

## When to revisit this doc

Update it after any phase that:
- Changes the shipped head (new accuracy number, new latency).
- Surfaces a new failure mode not covered by the three walls.
- Validates or refutes one of the improvement-lever projections.
- Reveals a new wall we hadn't identified.
